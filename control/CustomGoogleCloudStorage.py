####
####### This Script contains the standard functions for the Google Cloud Platform
####

import datetime
# Imports the Google Cloud client library
from google.cloud import firestore


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