import json
import logging
from typing import Callable

from google.cloud import pubsub_v1

ABORT_EXPERIMENT = "ABORT_EXPERIMENT"

START_EXPERIMENT = "START_EXPERIMENT"

START_EXPERIMENT = "START_EXPERIMENT"

START_THROUGHPUT = "START_THROUGHPUT"

RESPONSE_MEASUREMENTS = "RESPONSE_MEASUREMENTS"

SOURCE_SINK_TOPIC = "test-bench-source-sink-topic"
CONTROL_TOPIC = "test-bench-control-topic"


def send_message(topic_name, data, service_type):
    # function expects a json object as data

    # Google Cloud project ID
    projectId = "bdspro"

    # Create a publisher client
    publisher = pubsub_v1.PublisherClient()

    data = json.dumps(data)

    # Publish the message
    topic_path = publisher.topic_path(projectId, topic_name)
    publisher.publish(topic_path, data=data.encode('utf-8'), **{'service_type': service_type})


def abort_experiment():
    send_message(SOURCE_SINK_TOPIC, {}, ABORT_EXPERIMENT)
    send_message(CONTROL_TOPIC, {}, ABORT_EXPERIMENT)


def get_service_type(message):
    return message.attributes['service_type']


def get_data(message):
    return json.loads(message.data.decode('utf-8'))


class ResponseMeasurementsMessage:
    @staticmethod
    def is_of_type(message):
        return get_service_type(message) == RESPONSE_MEASUREMENTS

    def __init__(self, message) -> None:
        super().__init__()
        data = get_data(message)
        self.measurements = data['measurements']
        self.source_or_sink = data['source_or_sink']

    def __str__(self) -> str:
        return f"ResponseMeasurementsMessage:\nsource or sink: {self.source_or_sink}"


class StartExperimentMessage:

    @staticmethod
    def is_of_type(message):
        return get_service_type(message) == START_EXPERIMENT

    def __init__(self, message) -> None:
        super().__init__()
        assert get_service_type(message) == START_EXPERIMENT
        data = get_data(message)
        self.image_name = data['image_name']
        self.test_id = data['test_id']
        self.dataset_id = data['dataset_id']
        self.evaluation_id = data['evaluation_id']
        self.iterations = int(data['iterations'])
        self.delay = float(data['delay'])
        self.ramp_factor = float(data['ramp_factor'])

    def __str__(self) -> str:
        return f"ThroughputStartMessage:\nimage name: {self.image_name}\ntest id: {self.test_id}\nevaluation id: {self.evaluation_id}\ndataset id: {self.dataset_id}\niterations: {self.iterations}\ndelay: {self.delay}\nramp factor: {self.ramp_factor}"


class AbortExperimentMessage:
    @staticmethod
    def is_of_type(message):
        return get_service_type(message) == ABORT_EXPERIMENT

    def __init__(self, message) -> None:
        super().__init__()
        assert get_service_type(message) == ABORT_EXPERIMENT


class ThroughputStartMessage:
    @staticmethod
    def is_of_type(message):
        return get_service_type(message) == START_THROUGHPUT

    def __init__(self, message) -> None:
        super().__init__()
        assert get_service_type(message) == START_THROUGHPUT
        data = get_data(message)
        self.dataset_id = data['dataset_id']
        self.iterations = int(data['iterations'])
        self.delay = float(data['delay'])
        self.ramp_factor = float(data['ramp_factor'])
        self.test_id = data['test_id']

    def __str__(self) -> str:
        return f"ThroughputStartMessage:\ntest id: {self.test_id}\ndataset id: {self.dataset_id}\niterations: {self.iterations}\ndelay: {self.delay}\nramp factor: {self.ramp_factor}"


def start_experiment(image_name: str, iterations: int, delay: float, ramp_factor: float, test_id: str, dataset_id: str,
                     evaluation_id: str):
    data = {
        'image_name': image_name,
        'test_id': test_id,
        'dataset_id': dataset_id,
        'evaluation_id': evaluation_id,
        'iterations': iterations,
        'delay': delay,
        'ramp_factor': ramp_factor
    }
    send_message(CONTROL_TOPIC, data, START_EXPERIMENT)


def throughput_start(test_id: str, iterations: int, delay: float, ramp_factor: float, dataset_id: str):
    data = {
        'dataset_id': dataset_id,
        'iterations': iterations,
        'delay': delay,
        'ramp_factor': ramp_factor,
        'test_id': test_id,
    }
    send_message(SOURCE_SINK_TOPIC, data, START_THROUGHPUT)


def response_measurements(source_or_sink: str, measurements: dict):
    data = {
        'source_or_sink': source_or_sink,
        'measurements': measurements
    }

    print("Send throughput done message", flush=True)
    send_message(CONTROL_TOPIC, data, RESPONSE_MEASUREMENTS)


def subscribe_source(callback: Callable, logger: logging.Logger):
    # Your Google Cloud project ID
    projectId = "bdspro"
    # The name of the subscription
    subscriptionName = "test-bench-source-topic-sub"
    # create a subscriber client
    subscriber = pubsub_v1.SubscriberClient()
    # create a full path to the topic
    topicPath = subscriber.topic_path(projectId, SOURCE_SINK_TOPIC)
    # create a full path to the subscription
    subscriptionPath = subscriber.subscription_path(projectId, subscriptionName)
    # subscribe to the subscription
    future = subscriber.subscribe(subscriptionPath, callback)
    logger.info("Listening for messages on {}...".format(subscriptionPath))
    return future


def subscribe_sink(callback: Callable, logger: logging.Logger):
    # Your Google Cloud project ID
    projectId = "bdspro"
    # The name of the subscription
    subscriptionName = "test-bench-sink-topic-sub"
    # create a subscriber client
    subscriber = pubsub_v1.SubscriberClient()
    # create a full path to the topic
    topicPath = subscriber.topic_path(projectId, SOURCE_SINK_TOPIC)
    # create a full path to the subscription
    subscriptionPath = subscriber.subscription_path(projectId, subscriptionName)
    # subscribe to the subscription
    future = subscriber.subscribe(subscriptionPath, callback)
    logger.info("Listening for messages on {}...".format(subscriptionPath))
    return future


def subscribe_control(callback: Callable, logger: logging.Logger):
    # Your Google Cloud project ID
    projectId = "bdspro"
    # The name of the subscription
    subscriptionName = "test-bench-control-topic-sub"
    # create a subscriber client
    subscriber = pubsub_v1.SubscriberClient()
    # create a full path to the topic
    topicPath = subscriber.topic_path(projectId, CONTROL_TOPIC)
    # create a full path to the subscription
    subscriptionPath = subscriber.subscription_path(projectId, subscriptionName)
    # subscribe to the subscription
    future = subscriber.subscribe(subscriptionPath, callback)
    logger.info("Listening for messages on {}...".format(subscriptionPath))
    return future
