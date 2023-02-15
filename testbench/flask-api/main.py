from flask import Flask, request, jsonify

import testbench.common.LoggingFunctions as log
import testbench.common.UniqueIdGenerator as uid
from testbench.common.messages import abort_experiment, start_experiment

app = Flask(__name__)

logger = log.create_logger('flask-api')


@app.route('/')
def root():
    return 'Please give an argument to the URL.'


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

    # return datasetId, parameters
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

    # return datasetId, evaluationId, parameters
    response = {
        'datasetId': datasetId,
        'evaluationId': evaluationId,
        'message': 'Success',
        'parameters': allParams
    }

    return jsonify(response)


@app.route('/abort')
def abortExperiment():
    abort_experiment()


@app.route('/newExperiment')
def new_experiment_endpoint():
    dataset_id = request.args.get('datasetId')
    evaluation_id = request.args.get('evaluationId')
    image_name = request.args.get('imageName')
    github_token = request.args.get('githubToken')
    source_address = request.args.get('sourceAddress', None)
    source_port = int(request.args.get('sourcePort', None))
    sink_address = request.args.get('sinkAddress', None)
    sink_port = int(request.args.get('sinkPort', None))
    control_address = request.args.get('controlAddress', None)
    control_port = int(request.args.get('controlPort', None))
    operator = request.args.get('operator', 'identity')
    delay = float(request.args.get('delay', 0.1))
    iterations = int(request.args.get('iterations', 100))
    restarts = int(request.args.get('restarts', 0))
    sample_rate = int(request.args.get('sampleRate', 100))
    force_rebuild = request.args.get('forceRebuild').lower() == 'true'
    tuple_format = request.args.get('tupleFormat', "binary").lower()
    ramp_factor = 1.02

    if tuple_format not in ("json", "binary"):
        tuple_format = "binary"

    experiment_id = uid.generateUniqueExperimentId()

    start_experiment(control_port, control_address, sink_port, sink_address, source_port, source_address, operator,
                     github_token, image_name, iterations, delay, ramp_factor, experiment_id, dataset_id, evaluation_id,
                     force_rebuild, sample_rate, restarts, tuple_format)

    # return datasetId, evaluationId, parameters
    response = {
        'experimentId': experiment_id,
        'datasetId': dataset_id,
        'evaluationId': evaluation_id,
        'message': 'Success',
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
