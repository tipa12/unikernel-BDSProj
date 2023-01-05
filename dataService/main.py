from flask import Flask, render_template, request, jsonify
from tupleGenerator import generate_tuples
from google.cloud import firestore
# Imports the Google Cloud client library
from google.cloud import storage
import uuid
import datetime
import pickle

app = Flask(__name__)

@app.route('/')
def root():
    return 'Please give an argument to the URL.'

def generateUniqueDatasetId():
    # Generate a unique ID
    uniqueId = str(uuid.uuid4())

    # Get the current date and time
    now = datetime.datetime.now()

    # Format the date and time as a string
    dateTimeStr = now.strftime("%Y%m%d%H%M%S")

    # Concatenate the unique ID and the date/time string
    uniqueIdWithDateTime = 'ds-' + dateTimeStr + '-' + uniqueId

    return uniqueIdWithDateTime

def generateUniqueEvaluationId():
    # Generate a unique ID
    uniqueId = str(uuid.uuid4())

    # Get the current date and time
    now = datetime.datetime.now()

    # Format the date and time as a string
    dateTimeStr = now.strftime("%Y%m%d%H%M%S")

    # Concatenate the unique ID and the date/time string
    uniqueIdWithDateTime = 'ev-' + dateTimeStr + '-' + uniqueId

    return uniqueIdWithDateTime

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


@app.route('/generateDataset')
def generateDatasetEndpoint():
    allParams = request.args.to_dict()

    # set parameters/arguments
    sizeOfTuples = int(request.args.get('sizeOfTuples'))
    numberOfTuples = int(request.args.get('numberOfTuples'))
    elementType = request.args.get('elementType')
    elementRangeStart = int(request.args.get('elementRangeStart'))
    elementRangeEnd = int(request.args.get('elementRangeEnd'))
    name = request.args.get('name')

    # generate datasetId
    datasetId = generateUniqueDatasetId()
    if not request.args.get('name'):
        name = 'default'

    firestoreDict = {
        "name": name,
        "sizeOfTuples": sizeOfTuples,
        "numberOfTuples": numberOfTuples,
        "elementType": elementType,
        "elementRangeStart": elementRangeStart,
        "elementRangeEnd": elementRangeEnd,
        "datasetId": datasetId
    }

    createFirestoreDocument('datasets', datasetId, firestoreDict)

    # generate dataset
    generateDataset(datasetId, sizeOfTuples, numberOfTuples, elementType, elementRangeStart, elementRangeEnd)

    #return datasetId, parameters
    response = {
        'datasetId': datasetId,
        'message': 'Success',
        'parameters': allParams
    }
    return jsonify(response)


@app.route('/evaluateDataset')
def evaluateDatasetEndpoint():
    allParams = request.args.to_dict()
    # function to evaluate dataset: filter, map
    unikernelFunction = request.args.get('unikernelFunction')
    datasetId = request.args.get('datasetId')

    evaluationId = generateUniqueEvaluationId()

    firestoreDict = {
        "unikernelFunction": unikernelFunction,
        "datasetId": datasetId,
        "evaluationId": evaluationId
    }

    createFirestoreDocument('evaluations', evaluationId, firestoreDict)

    acceptedTuples, rejectedTuples = evaluateDataset(datasetId, unikernelFunction)

    updateDict = {
        "acceptedTuples": acceptedTuples,
        "rejectedTuples": rejectedTuples
    }

    updateFirestore('evaluations', evaluationId, updateDict)

    #return datasetId, evaluationId, parameters
    response = {
        'datasetId': datasetId,
        'evaluationId': evaluationId,
        'message': 'Success',
        'parameters': allParams
    }

    return jsonify(response)

if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)


