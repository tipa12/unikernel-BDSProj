# Imports the Google Cloud client library
import json
import time

from google.cloud import pubsub_v1

from testbench.common.LoggingFunctions import create_logger
import SendData as sd
from testbench.common.messages import ThroughputStartMessage, AbortExperimentMessage, subscribe_source, RestartMessage

logger = create_logger('source')


# use the subscriber client to create a subscription and a callback
def callback(message):
    message.ack()
    if ThroughputStartMessage.is_of_type(message):
        start_throughput_message = ThroughputStartMessage(message)
        logger.info(f"Start Throughput Message: {start_throughput_message}")
        sd.send_data(start_throughput_message, logger)
    elif RestartMessage.is_of_type(message):
        sd.restart_current_experiment(logger)
    elif AbortExperimentMessage.is_of_type(message):
        sd.abort_current_experiment(logger)
    else:
        service_type = message.attributes['serviceType']
        logger.error('Unknown serviceType: {}'.format(service_type))


future = subscribe_source(callback, logger)

# keep the main thread from exiting
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    future.cancel()
