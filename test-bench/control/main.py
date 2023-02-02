import time
import common.LoggingFunctions as log
from google.cloud import pubsub_v1
import ControlFunctions as control
import json

# create Logger
logger = log.createLogger()


# use the subscriber client to create a subscription and a callback
def callback(message):
    message.ack()
    service_type = message.attributes['serviceType']
    logger.info('Received serviceType Request: {}'.format(service_type))

    message_data = json.loads(message.data.decode('utf-8'))

    if service_type == 'startExperiment':
        logger.info("Start new experiment")
        control.start_experiment(message_data, logger)
    else:
        print('Unknown serviceType: {}'.format(service_type))
        logger.error('Unknown serviceType: {}'.format(service_type))


# Your Google Cloud project ID
projectId = "bdspro"
# The name of the Pub/Sub topic
topicName = "controlPipeline"
# The name of the subscription
subscriptionName = "controlPipeline-sub"

# create a subscriber client
subscriber = pubsub_v1.SubscriberClient()

# create a full path to the topic
topicPath = subscriber.topic_path(projectId, topicName)

# create a full path to the subscription
subscriptionPath = subscriber.subscription_path(projectId, subscriptionName)

# subscribe to the subscription
future = subscriber.subscribe(subscriptionPath, callback)

logger.info("Listening for messages on {}...".format(subscriptionPath))

# keep the main thread from exiting
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    future.cancel()
