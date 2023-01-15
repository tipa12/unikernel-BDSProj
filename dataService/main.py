import logging
from tupleGenerator import generate_tuples
from google.cloud import firestore
# Imports the Google Cloud client library
from google.cloud import storage
import datetime
import pickle
import time
from google.cloud import pubsub_v1
import json

app = Flask(__name__)

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


def tupleToDict(tuple):
    return {str(i): val for i, val in enumerate(tuple)}

def uploadObjectToCloudStorage(uniqueFilename, objectToUpload, bucketName):
    # Writing to tmp folder
    with open("/tmp/" + uniqueFilename + ".pkl", "wb") as file:
        # Serialize the list
        pickle.dump(objectToUpload, file)

    # Create a storage client
    storageClient = storage.Client()
    # Get a reference to the bucket
    bucket = storageClient.bucket(bucketName)
    # bucket = storage_client.get_bucket(bucketName)

    blob = bucket.blob(uniqueFilename + ".pkl")
    blob.upload_from_filename("/tmp/" + uniqueFilename + ".pkl")

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

def generateDataset(datasetId, sizeOfTuples, numberOfTuples, elementType, elementRangeStart, elementRangeEnd):

    # generate tuples
    listOfTuples = generate_tuples(sizeOfTuples, numberOfTuples, elementType, (elementRangeStart, elementRangeEnd))

    # bucket name for cloud storage
    bucketName = 'datasetbucket3245'

    uploadObjectToCloudStorage(datasetId, listOfTuples, bucketName)
    updateFirestore('datasets', datasetId, {'uploadedToCloudStorage': True, "datasetFilename": datasetId + ".pkl"})

    return datasetId

def evaluateDataset(datasetId, unikernelFunction, evaluationId):
    data = downloadDataset(datasetId)
    acceptedTuples = 0
    rejectedTuples = 0

    if unikernelFunction == 'filter':
        for tuple in data:
            if tuple[0] > 0:
                acceptedTuples += 1
            else:
                rejectedTuples += 1
    elif unikernelFunction == 'map':
        acceptedTuples = len(data)
    else:
        print("Error: Unikernel function not recognized")

    updateDict = {
        "acceptedTuples": acceptedTuples,
        "rejectedTuples": rejectedTuples
    }

    updateFirestore('evaluations', evaluationId, updateDict)


# use the subscriber client to create a subscription and a callback
def callback(message):
    print("Received message: {}".format(message))
    message.ack()
    functionName = message.attributes['functionName']
    data = message.data.decode('utf-8')
    jsonData = json.loads(data)

    print(jsonData)

    if functionName == 'generateDataset':
        generateDataset(jsonData['datasetId'], jsonData['sizeOfTuples'], jsonData['numberOfTuples'], jsonData['elementType'], jsonData['elementRangeStart'], jsonData['elementRangeEnd'])
    elif functionName == 'evaluateDataset':
        evaluateDataset(jsonData['datasetId'], jsonData['unikernelFunction'], jsonData['evaluationId'])

# Your Google Cloud project ID
projectId = "bdspro"

# The name of the Pub/Sub topic
topicName = "dataServicePipeline"

# The name of the subscription
subscriptionName = "dataServicePipeline-sub"

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