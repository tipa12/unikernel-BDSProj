import gc
import logging
import select
import socket
import struct
import threading
import time
from _socket import SHUT_WR, SHUT_RD
from typing import Union

import testbench.common.CustomGoogleCloudStorage as gcs
from testbench.common.experiment import ExperimentAbortedException, ExperimentAlreadyRunningException
from testbench.common.messages import ThroughputStartMessage, response_measurements
from testbench.common.stats import *

PORT = 8081


class TestContext:

    def __init__(self, logger: logging.Logger) -> None:
        super().__init__()

        self.adjust_backpressure_timestamps = []
        self.adjust_backpressure_acks_timestamps = []
        self.source_socket: socket.socket | None = None

        self.initial_packet_stats: PacketStats | None = None
        self.final_packet_stats: PacketStats | None = None
        self.diff_packet_stats: PacketStats | None = None

        self.tuple_timestamps = []
        self.number_of_tuples_sent = 0
        self.number_of_tuples_passing_the_filter = 0
        self.start_timestamp: float | None = None
        self.stop_timestamp: float | None = None

        self.logger = logger

        self.stop_event = threading.Event()

    def get_measurements(self) -> dict:
        return {
            "tuples_sent_timestamps": self.tuple_timestamps,
            "number_of_tuples_sent": self.number_of_tuples_sent,
            "number_of_tuples_passing_the_filter": self.number_of_tuples_passing_the_filter,
            "start_timestamp": self.start_timestamp,
            "stop_timestamp": self.stop_timestamp,
            "packets": vars(self.diff_packet_stats),
        }

    def clean_up(self):
        if self.source_socket is not None:
            self.source_socket.close()


def close_connection(context: TestContext, client_socket: socket.socket):
    context.logger.info("Closing Connection")
    client_socket.setblocking(True)
    client_socket.send(b"DONE")
    ack_message = client_socket.recv(4)
    context.stop_timestamp = time.perf_counter()
    context.logger.info("Waiting for ACK")
    context.logger.info(f"{ack_message}")
    assert ack_message == b"ACK"
    client_socket.close()
    context.logger.info("Connection closed")


def backpressure_adjustment(context: TestContext, client_socket: socket.socket):
    context.logger.info("Backpressure Adjustment")
    client_socket.setblocking(True)
    context.adjust_backpressure_timestamps.append(time.perf_counter())
    client_socket.send(b"BACK")
    context.logger.info("Waiting for ACK")
    ack_message = client_socket.recv(4)
    context.adjust_backpressure_acks_timestamps.append(time.perf_counter())
    assert ack_message == b"ACK"
    context.logger.info("Backpressure Adjusted")
    client_socket.setblocking(False)


def handle_client(client_socket: socket.socket, context: TestContext, data, delay: float, scale: int,
                  ramp_factor: float, packet_length=4):
    if len(data) % packet_length != 0:
        context.logger.warning("Size of dataset is not divisible by packet length, dataset will be truncated")
        data = data[:(len(data) // packet_length) * packet_length]

    struct_string = f"!{5 * packet_length}i"

    number_of_tuples = 0
    total = len(data) * scale

    start_message = client_socket.recv(len("SEND TUPLES!"))
    assert start_message == b"SEND TUPLES!"
    client_socket.setblocking(False)
    context.start_timestamp = time.perf_counter()
    time_stamp = time.perf_counter()

    for _ in range(scale):
        for i in range(0, len(data), packet_length):

            passing = [data[i + pi][0] > 0 for pi in range(packet_length)]

            data_tuple = [
                [data[i + pi][0], context.number_of_tuples_sent + pi, data[i + pi][2], data[i + pi][3], data[i + pi][4]]
                for pi in range(packet_length)]

            packet = [item for sub_list in data_tuple for item in sub_list]

            # pack the values into a byte string
            packed_data = struct.pack(struct_string, *packet)

            # Non-Blocking send
            # use downtime to log TPS
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
                        context.logger.info(f"TPS: {tuples_send_in_delta / delta} over the last {delta}s")
                        context.logger.info(f"{100 * context.number_of_tuples_sent / total}% done")

                    if context.stop_event.is_set():
                        raise ExperimentAbortedException()

                    time.sleep(repeat_if_blocking_delay)
                    counter += 1
                    if counter < 20:
                        repeat_if_blocking_delay *= 2
                    if counter == 20:
                        backpressure_adjustment(context, client_socket)
                    if counter > 20:
                        context.logger.warning(f"Blocking {counter}")

            context.number_of_tuples_sent += packet_length

            for p in passing:
                if p:
                    if context.number_of_tuples_passing_the_filter % scale // 10 == 0:
                        context.tuple_timestamps.append(time.perf_counter())

                    context.number_of_tuples_passing_the_filter += 1

            # Decrease the delay time - comment out to send data at a constant rate
            delay *= 1 / ramp_factor

            if context.stop_event.is_set():
                raise ExperimentAbortedException()

            if delay < 0.0001:
                continue

            time.sleep(delay)

    close_connection(context, client_socket)


def test_tuple_throughput(context: TestContext, data, delay, scale, ramp_factor, socket_opts=False):
    # Create a TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.setblocking(False)
    context.source_socket = server_socket

    if socket_opts:
        # Set the TCP_QUICKACK option
        server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_QUICKACK, 1)
        assert server_socket.getsockopt(socket.IPPROTO_TCP, socket.TCP_QUICKACK) == 1
        # Set the TCP_NODELAY option
        server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        assert server_socket.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY) == 1

    # Bind the socket to a local address and port
    server_socket.bind(('0.0.0.0', PORT))

    context.logger.info("Waiting for Connection")
    # Start listening for incoming connections
    server_socket.listen()

    inputs = [server_socket]

    while inputs:
        readable, writable, exceptional = select.select(inputs, [], [], 0.5)
        if not (readable or writable or exceptional):
            # select timeout
            if context.stop_event.is_set():
                context.logger.info("Aborting Experiment")
                return
            else:
                # repeat
                continue
        else:
            # we got a connection
            if context.stop_event.is_set():
                context.logger.info("Aborting Experiment")
                return

            # Accept a single incoming connection
            client_socket, client_address = server_socket.accept()

            if socket_opts:
                assert client_socket.getsockopt(socket.IPPROTO_TCP, socket.TCP_QUICKACK) == 1
                assert client_socket.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY) == 1

            context.logger.info(f"Producer: Accepted a connection from {client_address}")

            context.initial_packet_stats = PacketStats()
            # Handle the client's request
            handle_client(client_socket, context, data, delay, scale, ramp_factor)
            break


active_test_context: Union[TestContext, None] = None


def test_gcp(test_id: str, data, delay, iterations, logger, ramp_factor=1.05) -> TestContext:
    global active_test_context

    if active_test_context is not None:
        raise ExperimentAlreadyRunningException()

    active_test_context = TestContext(logger)
    try:
        test_tuple_throughput(active_test_context, data, delay, iterations, ramp_factor)

        active_test_context.final_packet_stats = PacketStats()

        active_test_context.diff_packet_stats = \
            diff(active_test_context.initial_packet_stats, active_test_context.final_packet_stats)

        gcs.store_evaluation_in_bucket(logger, active_test_context.get_measurements(), 'source', test_id)

        response_measurements('source', {})

    except ExperimentAbortedException as _:
        active_test_context.logger.info("Experiment was aborted")
    finally:
        active_test_context.clean_up()
        active_test_context = None
        gc.collect()

def abort_current_experiment(logger: logging.Logger):
    global active_test_context

    if active_test_context is not None:
        logger.warning(f"Request aborting the experiment")
        active_test_context.stop_event.set()


def send_data(message: ThroughputStartMessage, logger):
    data = gcs.downloadDataset(message.dataset_id)

    test_gcp(message.test_id, data, message.delay, message.iterations, logger)
