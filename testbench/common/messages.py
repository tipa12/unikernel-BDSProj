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
        as_str = "ResponseMeasurementsMessage\n"
        for k, v in vars(self).items():
            as_str += f"\t{k}: {v}\n"
        return as_str


class StartExperimentMessage:

    @staticmethod
    def is_of_type(message):
        return get_service_type(message) == START_EXPERIMENT

    def __init__(self, message) -> None:
        super().__init__()

        assert get_service_type(message) == START_EXPERIMENT
        data = get_data(message)
        self.force_rebuild = data['force_rebuild']
        self.control_port = data['control_port']
        self.control_address = data['control_address']
        self.sink_port = data['sink_port']
        self.sink_address = data['sink_address']
        self.source_port = data['source_port']
        self.source_address = data['source_address']
        self.operator = data['operator']
        self.github_token = data['github_token']
        self.image_name = data['image_name']
        self.test_id = data['test_id']
        self.dataset_id = data['dataset_id']
        self.evaluation_id = data['evaluation_id']
        self.iterations = int(data['iterations'])
        self.delay = float(data['delay'])
        self.ramp_factor = float(data['ramp_factor'])

    def __str__(self) -> str:
        as_str = "StartExperimentMessage\n"
        for k, v in vars(self).items():
            as_str += f"\t{k}: {v}\n"
        return as_str


class AbortExperimentMessage:
    @staticmethod
    def is_of_type(message):
        return get_service_type(message) == ABORT_EXPERIMENT

    def __init__(self, message) -> None:
        super().__init__()
        assert get_service_type(message) == ABORT_EXPERIMENT

    def __str__(self) -> str:
        as_str = "AbortExperimentMessage\n"
        for k, v in vars(self).items():
            as_str += f"\t{k}: {v}\n"
        return as_str


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
        as_str = "ThroughputStartMessage\n"
        for k, v in vars(self).items():
            as_str += f"\t{k}: {v}\n"
        return as_str


def start_experiment(control_port: int, control_address: str, sink_port: int, sink_address: str, source_port: int,
                     source_address: str, operator: str, github_token: str, image_name: str, iterations: int,
                     delay: float, ramp_factor: float, test_id: str, dataset_id: str, evaluation_id: str,
                     force_rebuild: bool):
    data = {
        'force_rebuild': force_rebuild,
        'control_port': control_port,
        'control_address': control_address,
        'sink_port': sink_port,
        'sink_address': sink_address,
        'source_port': source_port,
        'source_address': source_address,
        'operator': operator,
        'github_token': github_token,
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
