from flask import Flask, request, jsonify
from google.cloud import pubsub_v1
import json
import CustomGoogleCloudStorage  as gcs
import LoggingFunctions as log
import UniqueIdGenerator as uid

app = Flask(__name__)

logger = log.createLogger()

@app.route('/')
def root():
    return 'Please give an argument to the URL.'

def sendToMessageBroker(topicName, data, attributes={}):
    # function expects a json object as data

    # Google Cloud project ID
    projectId = "bdspro"

    # Create a publisher client
    publisher = pubsub_v1.PublisherClient()

    data = json.dumps(data)

    # Publish the message
    topic_path = publisher.topic_path(projectId, topicName)
    publisher.publish(topic_path, data=data.encode('utf-8'), **attributes)

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
    
    # limit number of tuples to 1 million
    if numberOfTuples > 1000000:
        numberOfTuples = 1000000

    # generate datasetId
    datasetId = uid.generateUniqueDatasetId()
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
    topicName = "sourcePipeline"

    sendToMessageBroker(topicName, datasetMetaDict, {'serviceType': 'generateDataset'})

    gcs.createFirestoreDocument('datasets', datasetId, datasetMetaDict)

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

    evaluationId = uid.generateUniqueEvaluationId()

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

    gcs.createFirestoreDocument('evaluations', evaluationId, evaluationMetaDict)

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
    iterations = int(request.args.get('iterations'))
    imageName = request.args.get('imageName')

    experimentId = uid.generateUniqueExperimentId()

    experimentMetaDict = {
        "experimentId": experimentId,
        "datasetId": datasetId,
        "evaluationId": evaluationId,
        "delay": delay,
        "iterations": iterations,
        "imageName": imageName
    }

    # Send data to control instance
    controlTopicName = "controlPipeline"

    controlPipelineMessage = {x:experimentMetaDict[x] for x in experimentMetaDict.keys()}

    sendToMessageBroker(controlTopicName, controlPipelineMessage, {'serviceType': 'startExperiment'})

    # Send data to source instance
    sourceTopicName = "sourcePipeline"

    sourcePipelineMessage = {x:experimentMetaDict[x] for x in experimentMetaDict.keys()}
    sourcePipelineMessage['port'] = 8081

    sendToMessageBroker(sourceTopicName, sourcePipelineMessage, {'serviceType': 'sendData'})

    # Send data to sink instance
    sinkTopicName = "sinkPipeline"

    sinkPipelineMessage = {x:experimentMetaDict[x] for x in experimentMetaDict.keys()}
    sinkPipelineMessage['port'] = 8081

    sendToMessageBroker(sinkTopicName, sinkPipelineMessage, {'serviceType': 'receiveData'})

    gcs.createFirestoreDocument('experiments', experimentId, experimentMetaDict)

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
