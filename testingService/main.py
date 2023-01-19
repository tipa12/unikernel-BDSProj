import datetime
import json
import logging
import pickle
import time

from google.cloud import firestore, storage
# Imports the Google Cloud client library
from google.cloud import pubsub_v1

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
        imageName = message['imageName']
        scale = message['scale']
        rampFactor = message['rampFactor']

        data = downloadDataset(datasetId)

        from experiments.gcp_experiment import test_gcp
        test_gcp(imageName, logger, data, delay, scale, rampFactor)


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
