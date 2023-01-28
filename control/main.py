import time
import LoggingFunctions as log
from google.cloud import pubsub_v1
import ControlFunctions as control

# create Logger
logger = log.createLogger()

# use the subscriber client to create a subscription and a callback
def callback(message):
    message.ack()
    serviceType = message.attributes['serviceType']

    if(serviceType == 'startExperiment'):
        logger.info("Start new experiment")
        control.startExperiment(message, logger)
    else:
        print('Unknown serviceType: {}'.format(serviceType))
        logger.error('Unknown serviceType: {}'.format(serviceType))

    print("Received message: {}".format(message))

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

print("Listening for messages on {}...".format(subscriptionPath))
logger.info("Listening for messages on {}...".format(subscriptionPath))

# keep the main thread from exiting
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    future.cancel()
