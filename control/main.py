import time
import LoggingFunctions as log
from google.cloud import pubsub_v1
import ControlFunctions as control
import json

# create Logger
logger = log.createLogger()

# use the subscriber client to create a subscription and a callback
def callback(message):
    message.ack()
    serviceType = message.attributes['serviceType']
    logger.info('Received serviceType Request: {}'.format(serviceType))

    messageData = json.loads(message.data.decode('utf-8'))

    if(serviceType == 'startExperiment'):
        logger.info("Start new experiment")
        # TODO Disable start of experiment when one is already running
        control.startExperiment(messageData, logger)
    else:
        print('Unknown serviceType: {}'.format(serviceType))
        logger.error('Unknown serviceType: {}'.format(serviceType))

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
