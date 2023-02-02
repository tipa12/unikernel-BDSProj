# Imports the Google Cloud client library
from google.cloud import pubsub_v1
import time
import json
import ReceiveData as rd
import common.LoggingFunctions as log

logger = log.createLogger()


# use the subscriber client to create a subscription and a callback
def callback(message):
    message.ack()
    service_type = message.attributes['serviceType']

    message_data = json.loads(message.data.decode('utf-8'))

    if service_type == 'receiveData':
        logger.info("Wait for data from Unikernel")
        rd.receive_data(message_data, logger)
    elif service_type == 'abort':
        rd.abort_current_experiment()
    else:
        print('Unknown serviceType: {}'.format(service_type))
        logger.error('Unknown serviceType: {}'.format(service_type))

    # message.datasetId

    # message.evaluationId

    # wie viele tuples

    # funktion von unikernel

    # adresse + port von evaluationService


# Your Google Cloud project ID
projectId = "bdspro"

# The name of the Pub/Sub topic
topicName = "sinkPipeline"

# The name of the subscription
subscriptionName = "sinkPipeline-sub"

# create a subscriber client
subscriber = pubsub_v1.SubscriberClient()

# create a full path to the topic
topicPath = subscriber.topic_path(projectId, topicName)

# create a full path to the subscription
subscriptionPath = subscriber.subscription_path(projectId, subscriptionName)

# subscribe to the subscription
future = subscriber.subscribe(subscriptionPath, callback)

print("Listening for messages on {}...".format(subscriptionPath))
logger.info("Listening for messages on {}...".format(subscriptionPath))

# keep the main thread from exiting
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    future.cancel()
