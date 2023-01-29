# Imports the Google Cloud client library
from google.cloud import pubsub_v1
import time
import json
import functions.ReceiveData as rd
import LoggingFunctions as log

logger = log.createLogger()


# use the subscriber client to create a subscription and a callback
def callback(message):
    message.ack()
    serviceType = message.attributes['serviceType']

    messageData = json.loads(message.data.decode('utf-8'))

    if(serviceType == 'receiveData'):
        logger.info("Wait for data from Unikernel")
        rd.receiveData(messageData, logger)
    else:
        print('Unknown serviceType: {}'.format(serviceType))
        logger.error('Unknown serviceType: {}'.format(serviceType))

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
