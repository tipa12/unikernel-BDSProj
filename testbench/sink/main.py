# Imports the Google Cloud client library
import time

from testbench.common.LoggingFunctions import createLogger
import ReceiveData as rd
from testbench.common.messages import ThroughputStartMessage, AbortExperimentMessage, subscribe_sink

logger = createLogger()


# use the subscriber client to create a subscription and a callback
def callback(message):
    message.ack()
    if ThroughputStartMessage.is_of_type(message):
        start_throughput_message = ThroughputStartMessage(message)
        logger.info(f"Start Throughput Message: {start_throughput_message}")
        rd.receive_data(start_throughput_message, logger)
    elif AbortExperimentMessage.is_of_type(message):
        rd.abort_current_experiment(logger)
    else:
        service_type = message.attributes['serviceType']
        logger.error('Unknown serviceType: {}'.format(service_type))


future = subscribe_sink(callback, logger)
# keep the main thread from exiting
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    future.cancel()
