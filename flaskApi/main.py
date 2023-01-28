import logging
from flask import Flask, render_template, request, jsonify
from google.cloud import firestore
import uuid
import datetime
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

def generateUniqueTestId():
    # Generate a unique ID
    uniqueId = str(uuid.uuid4())

    # Get the current date and time
    now = datetime.datetime.now()

    # Format the date and time as a string
    dateTimeStr = now.strftime("%Y%m%d%H%M%S")

    # Concatenate the unique ID and the date/time string
    uniqueIdWithDateTime = 'test-' + dateTimeStr + '-' + uniqueId

    return uniqueIdWithDateTime

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

def sendToMessageBroker(topicName, data, functionName):
    # function expects a json object as data

    # Google Cloud project ID
    projectId = "bdspro"

    # Create a publisher client
    publisher = pubsub_v1.PublisherClient()

    data = json.dumps(data)

    # Publish the message
    topic_path = publisher.topic_path(projectId, topicName)
    publisher.publish(topic_path, data=data.encode('utf-8'), functionName=functionName)

""" @app.route('/start/gcp/<image_name>')
def start_gcp(image_name: str):
    from experiments.gcp_experiment import test_gcp
    test_gcp(image_name, logger)


@app.route('/setup/gcp')
def setup_unikraft():
    from builder.unikraft_gcp_builder import setup_unikraft_image_for_gce
    setup_unikraft_image_for_gce(logger)

@app.route('/startTest')
def startTest():
    datasetId = request.args.get('datasetId')
    evaluationId = request.args.get('evaluationId')
    delay = float(request.args.get('delay'))
    imageName = request.args.get('imageName')
    
    data = downloadDataset(datasetId)

    from experiments.gcp_experiment import test_gcp
    test_gcp(imageName, logger, data, delay)

    return "OK" """

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
    
    if numberOfTuples > 1000000:
        numberOfTuples = 1000000

    # generate datasetId
    datasetId = generateUniqueDatasetId()
    if not request.args.get('name'):
        name = 'default'

    datasetMetaDict = {
        "name": name,
        "sizeOfTuples": sizeOfTuples,
        "numberOfTuples": numberOfTuples,
        "elementType": elementType,
        "elementRangeStart": elementRangeStart,
        "elementRangeEnd": elementRangeEnd,
        "datasetId": datasetId
    }
    # connect to message broker
    # generate dataset
    
    # The name of the Pub/Sub topic
    topicName = "dataServicePipeline"

    sendToMessageBroker(topicName, datasetMetaDict, 'generateDataset')

    createFirestoreDocument('datasets', datasetId, datasetMetaDict)

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

    evaluationMetaDict = {
        "unikernelFunction": unikernelFunction,
        "datasetId": datasetId,
        "evaluationId": evaluationId
    }

    # connect to message broker
    # generate dataset

    # The name of the Pub/Sub topic
    topicName = "dataServicePipeline"

    sendToMessageBroker(topicName, evaluationMetaDict, 'evaluateDataset')

    createFirestoreDocument('evaluations', evaluationId, evaluationMetaDict)

    #return datasetId, evaluationId, parameters
    response = {
        'datasetId': datasetId,
        'evaluationId': evaluationId,
        'message': 'Success',
        'parameters': allParams
    }

    return jsonify(response)

@app.route('/newExperiment')
def newExperimentEndpoint():
    allParams = request.args.to_dict()

    datasetId = request.args.get('datasetId')
    evaluationId = request.args.get('evaluationId')
    delay = float(request.args.get('delay'))
    numberOfTuples = int(request.args.get('numberOfTuples'))
    imageName = request.args.get('imageName')

    experimentId = generateUniqueTestId()

    experimentMetaDict = {
        "experimentId": experimentId,
        "datasetId": datasetId,
        "evaluationId": evaluationId,
        "delay": delay,
        "numberOfTuples": numberOfTuples,
        "imageName": imageName
    }

    createFirestoreDocument('experiments', experimentId, experimentMetaDict)

    # Send data to control instance
    controlTopicName = "controlPipeline"

    controlPipelineMessage = {x:experimentMetaDict[x] for x in experimentMetaDict.keys()}

    sendToMessageBroker(controlTopicName, controlPipelineMessage)

    # Send data to source instance
    sourceTopicName = "sourcePipeline"

    sourcePipelineMessage = {x:experimentMetaDict[x] for x in experimentMetaDict.keys()}
    sourcePipelineMessage['port'] = 8081

    sendToMessageBroker(sourceTopicName, sourcePipelineMessage)

    # Send data to sink instance
    sinkTopicName = "sinkPipeline"

    sinkPipelineMessage = {x:experimentMetaDict[x] for x in experimentMetaDict.keys()}
    sinkPipelineMessage['port'] = 8081

    sendToMessageBroker(sinkTopicName, sinkPipelineMessage)

    #return datasetId, evaluationId, parameters
    response = {
        'experimentId': experimentId,
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
