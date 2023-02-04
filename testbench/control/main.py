import time

import ControlFunctions as cc

import testbench.common.LoggingFunctions as log
# create Logger
from testbench.common.messages import subscribe_control, AbortExperimentMessage, StartExperimentMessage, \
    ResponseMeasurementsMessage
logger = log.createLogger()


# use the subscriber client to create a subscription and a callback
def callback(message):
    message.ack()
    logger.info("Message Received")
    if StartExperimentMessage.is_of_type(message):
        start_experiment_message = StartExperimentMessage(message)
        logger.info(f"Start Experiment Message: {start_experiment_message}")
        cc.launch_experiment(start_experiment_message, logger)
    elif ResponseMeasurementsMessage.is_of_type(message):
        measurements_message = ResponseMeasurementsMessage(message)
        logger.info(f"ResponseMeasurementsMessage: {measurements_message}")
        if measurements_message.source_or_sink == 'source':
            cc.source_is_done(measurements_message.measurements)
        elif measurements_message.source_or_sink == 'sink':
            cc.sink_is_done(measurements_message.measurements)
        else:
            logger.error(f"Expected source or sink, got: {measurements_message.source_or_sink}")
    elif AbortExperimentMessage.is_of_type(message):
        logger.warning(f"Abort Message")
        cc.abort_current_experiment(logger)
    else:
        service_type = message.attributes['serviceType']
        logger.error('Unknown serviceType: {}'.format(service_type))


future = subscribe_control(callback, logger)

try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    future.cancel()
