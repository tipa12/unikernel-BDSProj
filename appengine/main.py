from flask import Flask, render_template, request
from tupleGenerator import generate_tuples
from google.cloud import firestore
# Imports the Google Cloud client library
from google.cloud import storage
import uuid
import datetime
import pickle
import json

app = Flask(__name__)

@app.route('/')
def root():
    return 'Please give an argument to the URL.'

def oldWriteToFirestore():

    datasetId = generateUniqueID()

    # Create a Firestore client
    db = firestore.Client()

    # Create a new document in the "datasets" collection
    doc_ref = db.collection("datasets").document(datasetId)

    listOftuples = []

    ######################################
    tuplesCollection = db.collection("datasets").document(datasetId).collection("tuples")

    # Set the batch size
    batch_size = 500

    # Initialize the counter
    counter = 0

    batch = db.batch()

    # Loop through the documents
    for index, tuple in enumerate(listOftuples):
        tupleDict = tupleToDict(tuple)
        docRef = tuplesCollection.document(str(index))
        batch.set(docRef, tupleDict)

        # Increment the counter
        counter += 1
    
        # If the batch size is reached, add the documents to the collection in a batch
        if counter == batch_size:
            # Commit the batch and reset batch
            batch.commit()
            batch = db.batch()
            # Reset the counter
            counter = 0

    batch.commit()

def generateUniqueID():
    # Generate a unique ID
    unique_id = str(uuid.uuid4())

    # Get the current date and time
    now = datetime.datetime.now()

    # Format the date and time as a string
    date_time_str = now.strftime("%Y%m%d%H%M%S")

    # Concatenate the unique ID and the date/time string
    unique_id_with_date_time = date_time_str + "-" + unique_id

    return unique_id_with_date_time

def tupleToDict(tuple):
    return {str(i): val for i, val in enumerate(tuple)}

def serializeTupleListToPickle(listOfTuples):
    # Pickle the list
    pickledData = pickle.dumps(listOfTuples)
    return (".pkl", pickledData)

    # Open the file in read mode
    #with open('my_list.pkl', 'rb') as f:
        # Load the list from the file
    #    my_list = pickle.load(f)

    #print(my_list)  # Output: [(1,9,3),(6,4,1),(9,3,5),(6,4,3)]

def serializeTupleListToJson(listOfTuples):
    # Convert the list to a JSON string
    jsonData = json.dumps(listOfTuples)
    return (".json", jsonData)


def uploadTupleListToCloudStorage1(listOfTuples, bucketName, datasetId):
    fileNameTemplate = datasetId + "_{}.json"
    # Split the list into smaller chunks
    chunkSize = 10000
    numChunks = len(listOfTuples) // chunkSize
    if len(listOfTuples) % chunkSize != 0:
        numChunks += 1
    for i in range(numChunks):
        chunk = listOfTuples[i*chunkSize:(i+1)*chunkSize]
    
        # Convert the chunk to a JSON string
        jsonData = json.dumps(chunk)

        # Create a storage client
        storageClient = storage.Client()

        # Get a reference to the bucket
        bucket = storageClient.bucket(bucketName)
        # bucket = storage_client.get_bucket(bucketName)

        # Create a blob from the file
        fileName = fileNameTemplate.format(i)
        blob = bucket.blob(datasetId + "/" + fileName)

        # Upload the JSON data to the bucket
        blob.upload_from_string(jsonData)

def uploadTupleListToCloudStorage2(listOfTuples, bucketName, datasetId):
    # Serialize the list
    data = pickle.dumps(listOfTuples)

    # Save the serialized list to a temporary file
    import tempfile
    with tempfile.NamedTemporaryFile() as fp:
        fp.write(data)
        fp.flush()

    # Create a storage client
    storageClient = storage.Client()
    # Get a reference to the bucket
    bucket = storageClient.bucket(bucketName)
    # bucket = storage_client.get_bucket(bucketName)


    blob = bucket.blob(datasetId + ".pkl")
    blob.upload_from_filename(fp.name)


def writeDatasetToDatabase(name, sizeOfTuples, numberOfTuples, elementType, elementRangeStart, elementRangeEnd, listOfTuples):

    datasetId = generateUniqueID()

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
        "tuplesLocation": "dummy"
    })

    #fileEnd, datasetData = serializeTupleListToJson(listOftuples)

    # Define the bucket and object name
    bucketName = 'datasetbucket3245'

    uploadTupleListToCloudStorage2(listOfTuples, bucketName, datasetId)

    return datasetId


@app.route('/generateDataset')
def generateDataset():
    # set parameters/arguments
    sizeOfTuples = int(request.args.get('sizeOfTuples'))
    numberOfTuples = int(request.args.get('numberOfTuples'))
    elementType = request.args.get('elementType')
    elementRangeStart = int(request.args.get('elementRangeStart'))
    elementRangeEnd = int(request.args.get('elementRangeEnd'))

    # generate tuples
    listOfTuples = generate_tuples(sizeOfTuples, numberOfTuples, elementType, (elementRangeStart, elementRangeEnd))
    datasetId = writeDatasetToDatabase("default", sizeOfTuples, numberOfTuples, elementType, elementRangeStart, elementRangeEnd, listOfTuples)

    #return tuples
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


