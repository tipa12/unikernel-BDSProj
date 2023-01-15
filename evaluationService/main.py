import logging
from google.cloud import firestore
# Imports the Google Cloud client library
from google.cloud import storage

from google.cloud import pubsub_v1
import uuid
import datetime
import pickle
import asyncio

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


def root():
    return 'Please give an argument to the URL.'

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

def evaluateDataset(datasetId, unikernelFunction):
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

    return acceptedTuples, rejectedTuples

subscriber = pubsub_v1.SubscriberClient()
