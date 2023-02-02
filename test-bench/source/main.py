# Imports the Google Cloud client library
import json
import time

from google.cloud import pubsub_v1

from common import LoggingFunctions as log
import source.SendData as sd

logger = log.createLogger()


# use the subscriber client to create a subscription and a callback
def callback(message):
    message.ack()
    service_type = message.attributes['serviceType']
    logger.info('Received serviceType Request: {}'.format(service_type))

    message_data = json.loads(message.data.decode('utf-8'))

    if service_type == 'sendData':
        logger.info("Starting: sendData")
        sd.send_data(message_data, logger)
    elif service_type == 'abort':
        sd.abort_current_experiment()
    else:
        logger.error('Unknown serviceType: {}'.format(service_type))


# Your Google Cloud project ID
projectId = "bdspro"

# The name of the Pub/Sub topic
topicName = "sourcePipeline"

# The name of the subscription
subscriptionName = "sourcePipeline-sub"

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
