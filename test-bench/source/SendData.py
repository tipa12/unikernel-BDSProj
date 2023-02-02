import logging
import socket
import struct
import threading
import time
import common.CustomGoogleCloudStorage as gcs
from common.experiment import ExperimentAbortedException, ExperimentAlreadyRunningException

from common.stats import *

PORT = 8081

class TestContext:

    def __init__(self, logger: logging.Logger) -> None:
        super().__init__()

        self.source_socket: socket.socket | None = None
        self.initial_packet_stats: PacketStats | None = None
        self.final_packet_stats: PacketStats | None = None
        self.diff_packet_stats: PacketStats | None = None

        self.tuple_timestamps = []
        self.number_of_tuples_sent = 0
        self.number_of_tuples_passing_the_filter = 0

        self.logger = logger

        self.stop_event = threading.Event()

    def clean_up(self):
        if self.source_socket is not None:
            self.source_socket.close()


global active_test_context


def handle_client(client_socket: socket.socket, context: TestContext, data, delay, scale, ramp_factor):
    # Send data to the client at an increasing rate
    client_socket.setblocking(False)

    time_stamp = time.perf_counter()
    number_of_tuples = 0

    for _ in range(scale):
        for data_tuple in data:
            data_tuple = (data_tuple[0], context.number_of_tuples_sent, data_tuple[2], data_tuple[3], data_tuple[4])

            # logger.info(f"Sending: ${tuple}")
            # pack the values into a byte string
            packed_data = struct.pack('!5i', *data_tuple)

            # Send the data to the client
            repeat_if_blocking_delay = 0.000001
            counter = 0
            while True:
                try:
                    client_socket.send(packed_data)
                    break
                except BlockingIOError as e:
                    if counter == 0:
                        delta = time_stamp
                        time_stamp = time.perf_counter()
                        delta = time_stamp - delta
                        tuples_send_in_delta = context.number_of_tuples_sent - number_of_tuples
                        number_of_tuples = context.number_of_tuples_sent
                        print(f"TPS: {tuples_send_in_delta / delta} over the last {delta}s\n")

                    counter += 1
                    time.sleep(repeat_if_blocking_delay)
                    repeat_if_blocking_delay *= 2

            context.number_of_tuples_sent += 1

            if data_tuple[0] > 0:
                if context.number_of_tuples_passing_the_filter % scale // 100 == 0:
                    context.tuple_timestamps.append(time.perf_counter())
                context.number_of_tuples_passing_the_filter += 1

            # Decrease the delay time - comment out to send data at a constant rate
            delay *= 1 / ramp_factor

            if context.stop_event.is_set():
                raise ExperimentAbortedException()

            if delay < 0.0001:
                continue

            time.sleep(delay)

    print()
    context.logger.info("Sending Done")

    # make sure packets are flushed
    time.sleep(5)


def test_tuple_throughput(context: TestContext, data, delay, scale, ramp_factor, socket_opts=False):
    # Create a TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    if socket_opts:
        # Set the TCP_QUICKACK option
        server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_QUICKACK, 1)
        assert server_socket.getsockopt(socket.IPPROTO_TCP, socket.TCP_QUICKACK) == 1
        # Set the TCP_NODELAY option
        server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        assert server_socket.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY) == 1

    context.source_socket = server_socket

    # Bind the socket to a local address and port
    server_socket.bind(('0.0.0.0', PORT))

    # Start listening for incoming connections
    server_socket.listen()

    # Accept a single incoming connection
    client_socket, client_address = server_socket.accept()

    if socket_opts:
        assert client_socket.getsockopt(socket.IPPROTO_TCP, socket.TCP_QUICKACK) == 1
        assert client_socket.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY) == 1

    context.logger.info(f"Producer: Accepted a connection from {client_address}")

    time.sleep(5)
    context.init_stats = get_current_packet_loss()
    # Handle the client's request
    handle_client(client_socket, context, data, delay, scale, ramp_factor)


def test_gcp(data, delay, iterations, logger, ramp_factor=1.05) -> TestContext:
    global active_test_context

    if active_test_context is not None:
        raise ExperimentAlreadyRunningException()

    active_test_context = TestContext(logger)
    try:
        active_test_context.initial_packet_stats = get_current_packet_loss()

        test_tuple_throughput(active_test_context, data, delay, iterations, ramp_factor)

        active_test_context.final_packet_stats = get_current_packet_loss()

        active_test_context.diff_packet_stats = \
            diff(active_test_context.initial_packet_stats, active_test_context.final_packet_stats)

        return active_test_context

    except ExperimentAbortedException as _:
        active_test_context.logger.info("Experiment was aborted")
    finally:
        active_test_context.clean_up()
        active_test_context = None


def abort_current_experiment():
    global active_test_context

    if active_test_context is not None:
        active_test_context.stop_event.set()


def send_data(message_data, logger):
    if 'datasetId' not in message_data:
        logger.error("No datasetId given")
        return
    if 'delay' not in message_data:
        logger.error("No delay to send")
        return
    if 'iterations' not in message_data:
        logger.error("No iterations given")
        return

    dataset_id = message_data['datasetId']
    delay = float(message_data['delay'])
    iterations = int(message_data['iterations'])

    data = gcs.downloadDataset(dataset_id)

    test_gcp(data, delay, iterations, logger)
