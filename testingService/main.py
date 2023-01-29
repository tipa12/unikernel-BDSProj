import datetime
import json
import logging
import pickle
import time

from google.cloud import firestore, storage
# Imports the Google Cloud client library
from google.cloud import pubsub_v1

from experiments.gcp_experiment import TestContext

logger = logging.getLogger("Logger")
logger.setLevel(logging.DEBUG)
# Create a console handler
console_handler = logging.StreamHandler()
# Set the console handler level to DEBUG
console_handler.setLevel(logging.DEBUG)
# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Set the formatter for the console handler
console_handler.setFormatter(formatter)
# Add the console handler to the logger
logger.addHandler(console_handler)


def updateFirestore(collection, documentId, updateDict):
    # Create a Firestore client
    db = firestore.Client()

    # Create a new document in the "datasets" collection
    docRef = db.collection(collection).document(documentId)
    updateDict.update({'lastmodified': datetime.datetime.now()})

    # Set the data for the document
    docRef.update(updateDict)


def createFirestoreDocument(collection, documentId, setDict):
    # Create a Firestore client
    db = firestore.Client()
    # Create a new document in the "datasets" collection
    docRef = db.collection(collection).document(documentId)
    setDict.update({"created": datetime.datetime.now(), 'lastmodified': datetime.datetime.now()})
    # Set the data for the document
    docRef.set(setDict)


def downloadDataset(datasetId):
    # Set up the Cloud Storage client
    client = storage.Client()

    # Set the name of the bucket and the file to download
    bucketName = "datasetbucket3245"
    fileName = datasetId + ".pkl"

    # Use the client to download the file
    bucket = client.bucket(bucketName)
    blob = bucket.blob(fileName)
    file = blob.download_as_string()

    # Deserialize the data from the file
    data = pickle.loads(file)

    return data


# use the subscriber client to create a subscription and a callback
def callback(message):
    print("Received message: {}".format(message.data))
    message.ack()
    message = json.loads(message.data)
    if message['type'] == "START":
        datasetId = message['datasetId']
        evaluationId = message['evaluationId']
        delay = float(message['delay'])
        image_name = message['imageName']
        scale = message['scale']
        ramp_factor = message['rampFactor']

        data = downloadDataset(datasetId)

        from experiments.gcp_experiment import test_gcp
        context = test_gcp(image_name, logger, data, delay, scale, ramp_factor)

        if context is None:
            raise "Experiment Failed"

        store_evaluation(context, {
            "image_name": image_name,
            "scale": scale,
            "delay": delay,
            "ramp_factor": ramp_factor,
            "dataset_id": datasetId
        })


def store_evaluation(context: TestContext, parameters):
    evaluation_data = {
        "number_of_tuples_sent": context.number_of_tuples_sent,
        "number_of_expected_tuples": context.number_of_expected_tuples,
        "number_of_tuples_recv": context.number_of_tuples_recv,
        "tuples_send_timestamps": context.tuples_send_timestamps,
        "tuples_received_timestamps": context.tuples_received_timestamps,
        "uut_serial": context.uut_serial_log,
        "packets_during_setup": {
            "sent": context.packets_during_setup[0],
            "received": context.packets_during_setup[1],
            "dropin": context.packets_during_setup[2],
            "dropout": context.packets_during_setup[3],
        },
        "packets_during_evaluation": {
            "sent": context.packets_during_evaluation[0],
            "received": context.packets_during_evaluation[1],
            "dropin": context.packets_during_evaluation[2],
            "dropout": context.packets_during_evaluation[3],
        }
    }

    # Create a Firestore client
    db = firestore.Client()
    # Create a new document in the "datasets" collection
    evaluation_collection = db.collection("evaluations")
    evaluation_collection.add(
        {"created": datetime.datetime.now(), 'data': evaluation_data, 'parameters': parameters}, str(context.test_id))

    context.logger.info(f"Evalutation was saved in Firestore: /evalutations/{context.test_id}")

# Your Google Cloud project ID
projectId = "bdspro"

# The name of the Pub/Sub topic
topicName = "testingServicePipeline"

# The name of the subscription
subscriptionName = "testingServicePipeline-sub"

# create a subscriber client
subscriber = pubsub_v1.SubscriberClient()

# create a full path to the topic
topicPath = subscriber.topic_path(projectId, topicName)

# create a full path to the subscription
subscriptionPath = subscriber.subscription_path(projectId, subscriptionName)

# subscribe to the subscription
future = subscriber.subscribe(subscriptionPath, callback)

print("Listening for messages on {}...".format(subscriptionPath))

# keep the main thread from exiting
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    future.cancel()
