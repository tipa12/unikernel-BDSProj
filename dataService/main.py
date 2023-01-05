import logging

from flask import Flask, render_template, request

from tupleGenerator import generate_tuples
from google.cloud import firestore
# Imports the Google Cloud client library
from google.cloud import storage
import uuid
import datetime
import pickle

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


@app.route('/')
def root():
    return 'Please give an argument to the URL.'


def generateUniqueID():
    # Generate a unique ID
    uniqueId = str(uuid.uuid4())

    # Get the current date and time
    now = datetime.datetime.now()

    # Format the date and time as a string
    dateTimeStr = now.strftime("%Y%m%d%H%M%S")

    # Concatenate the unique ID and the date/time string
    uniqueIdWithDateTime = dateTimeStr + "-" + uniqueId

    return uniqueIdWithDateTime


def tupleToDict(tuple):
    return {str(i): val for i, val in enumerate(tuple)}


def uploadObjectToCloudStorage(objectToUpload, bucketName, uniqueFilename):
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


def writeDatasetToFirestoreAndCloudStorage(name, sizeOfTuples, numberOfTuples, elementType, elementRangeStart,
                                           elementRangeEnd, listOfTuples, unikernelFunction):
    datasetId = generateUniqueID()
    # Define the bucket and object name
    bucketName = 'datasetbucket3245'

    # Create a Firestore client
    db = firestore.Client()

    # Create a new document in the "datasets" collection
    doc_ref = db.collection("datasets").document(datasetId)

    # Set the data for the document
    doc_ref.set({
        "name": name,
        "sizeOfTuples": sizeOfTuples,
        "numberOfTuples": numberOfTuples,
        "elementType": elementType,
        "elementRangeStart": elementRangeStart,
        "elementRangeEnd": elementRangeEnd,
        "cloudStorageBucket": bucketName,
        "datasetFilename": datasetId + ".pkl",
        "datasetId": datasetId,
        "dateCreated": datetime.datetime.now(),
        "unikernelFunction": unikernelFunction
    })
    uploadObjectToCloudStorage(listOfTuples, bucketName, datasetId)
    return datasetId


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

    # Create a Firestore client
    db = firestore.Client()

    # Create a new document in the "datasets" collection
    doc_ref = db.collection("datasets").document(datasetId)

    # Set the capital field
    doc_ref.update({
        'acceptedTuples': acceptedTuples,
        'rejectedTuples': rejectedTuples
    })


@app.route('/start/gcp/<image_name>')
def start_gcp(image_name: str):
    from experiments.gcp_experiment import test_gcp
    test_gcp(image_name, logger)


@app.route('/setup/gcp')
def setup_unikraft():
    from builder.unikraft_gcp_builder import setup_unikraft_image_for_gce
    setup_unikraft_image_for_gce(logger)


@app.route('/generateDataset')
def generateDatasetEndpoint():
    # set parameters/arguments
    sizeOfTuples = int(request.args.get('sizeOfTuples'))
    numberOfTuples = int(request.args.get('numberOfTuples'))
    elementType = request.args.get('elementType')
    elementRangeStart = int(request.args.get('elementRangeStart'))
    elementRangeEnd = int(request.args.get('elementRangeEnd'))
    unikernelFunction = request.args.get('unikernelFunction')

    # generate tuples
    listOfTuples = generate_tuples(sizeOfTuples, numberOfTuples, elementType, (elementRangeStart, elementRangeEnd))
    datasetId = writeDatasetToFirestoreAndCloudStorage("default", sizeOfTuples, numberOfTuples, elementType,
                                                       elementRangeStart, elementRangeEnd, listOfTuples,
                                                       unikernelFunction)

    # return tuples
    return datasetId


@app.route('/evaluateDataset')
def evaluateDatasetEndpoint():
    datasetId = request.args.get('datasetId')
    evaluateDataset(datasetId, 'filter')
    return datasetId


if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
