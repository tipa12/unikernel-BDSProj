import logging
import select
import socket
import struct
import threading
import time
import gc
from datetime import datetime
from typing import Union

import testbench.common.CustomGoogleCloudStorage as gcs
from testbench.common.experiment import ExperimentAbortedException, ExperimentAlreadyRunningException
from testbench.common.messages import ThroughputStartMessage, response_measurements
from testbench.common.stats import PacketStats, diff

PORT = 8081


class TestContext:

    def __init__(self, logger: logging.Logger) -> None:
        super().__init__()

        self.start_timestamp: float | None = None
        self.start_datetime: datetime | None = None

        self.done_timestamp: float | None = None

        self.sink_socket: socket.socket | None = None

        self.initial_packet_stats: PacketStats | None = None
        self.final_packet_stats: PacketStats | None = None
        self.diff_packet_stats: PacketStats | None = None

        self.tuples_received_timestamps = []
        self.number_of_tuples_recv = 0

        self.logger = logger
        self.abort_or_error = True
        self.stop_event = threading.Event()

    def get_measurements(self) -> dict:
        return {
            "abort_or_error": self.abort_or_error,
            "start_timestamp": self.start_timestamp,
            "start_datetime": self.start_datetime,
            "done_timestamp": self.done_timestamp,
            "tuples_received_timestamps": self.tuples_received_timestamps,
            "number_of_tuples_recv": self.number_of_tuples_recv,
            "packets": vars(self.diff_packet_stats),
        }

    def clean_up(self):
        if self.sink_socket is not None:
            self.sink_socket.close()


MAX_RECV_BUFFER_SIZE_IN_BYTES = 4096
TUPLE_SIZE_IN_BYTES = 20


def handle_client_receiver(client_socket: socket.socket, context: TestContext, scale: int):
    client_socket.setblocking(False)
    time_stamp = time.perf_counter()
    number_of_tuples = 0
    is_done = False
    while not is_done:
        if context.stop_event.is_set():
            raise ExperimentAbortedException()

        repeat_if_blocking_delay = 0.000001
        counter = 0
        while True:
            try:
                data = client_socket.recv(TUPLE_SIZE_IN_BYTES * 100)
                break
            except BlockingIOError as e:
                if context.stop_event.is_set():
                    raise ExperimentAbortedException()

                delta = time_stamp
                current = time.perf_counter()
                delta = current - delta
                if counter == 0 and delta > 5:
                    time_stamp = current
                    tuples_send_in_delta = context.number_of_tuples_recv - number_of_tuples
                    number_of_tuples = context.number_of_tuples_recv
                    context.logger.info(f"TPS: {tuples_send_in_delta / delta} over the last {delta}s\n")

                if counter > 30:
                    context.logger.info("Receive timeout")
                    data = []
                    break

                counter += 1
                time.sleep(repeat_if_blocking_delay)
                repeat_if_blocking_delay *= 2

        if len(data) == 0:
            break

        if len(data) % TUPLE_SIZE_IN_BYTES != 0:
            if len(data) % TUPLE_SIZE_IN_BYTES == 4:
                context.done_timestamp = time.perf_counter()
                print(data[-4:])
                assert data[-4:] == b"DONE"
                client_socket.send(b"ACK")
                is_done = True

        for i in range(len(data) // TUPLE_SIZE_IN_BYTES):
            received_tuple = struct.unpack(f'!5i', data[i * TUPLE_SIZE_IN_BYTES:(i + 1) * TUPLE_SIZE_IN_BYTES])
            if context.number_of_tuples_recv % scale // 10 == 0:
                context.tuples_received_timestamps.append(time.perf_counter())

            context.number_of_tuples_recv += 1

    context.logger.info("Receiving Done!")


def test_tuple_throughput_receiver(context: TestContext, scale):
    # Create a TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.setblocking(False)
    context.sink_socket = server_socket

    # Bind the socket to a local address and port
    server_socket.bind(('0.0.0.0', PORT))

    context.logger.info("Waiting for Connection")
    # Start listening for incoming connections
    server_socket.listen(1)

    inputs = [server_socket]

    while inputs:
        readable, writable, exceptional = select.select(inputs, [], [], 0.5)
        if not (readable or writable or exceptional):
            # select timeout
            if context.stop_event.is_set():
                raise ExperimentAbortedException()
            else:
                # repeat
                continue
        else:
            # we got a connection
            if context.stop_event.is_set():
                raise ExperimentAbortedException()

            # Accept a single incoming connection
            client_socket, client_address = server_socket.accept()
            context.start_datetime = datetime.now()
            context.start_timestamp = time.perf_counter()
            context.logger.info(f"Receiver: Accepted a connection from {client_address}")

            context.initial_packet_stats = PacketStats()
            try:
                # Handle the client's request
                handle_client_receiver(client_socket, context, scale)
                break
            finally:
                client_socket.close()


active_test_context: Union[TestContext, None] = None


def receive_data(message: ThroughputStartMessage, logger):
    global active_test_context

    if active_test_context is not None:
        raise ExperimentAlreadyRunningException()

    active_test_context = TestContext(logger)

    try:
        test_tuple_throughput_receiver(active_test_context, scale=message.iterations)
        active_test_context.final_packet_stats = PacketStats()

        active_test_context.diff_packet_stats = \
            diff(active_test_context.initial_packet_stats, active_test_context.final_packet_stats)

        active_test_context.abort_or_error = False
        gcs.store_evaluation_in_bucket(logger, active_test_context.get_measurements(), 'sink', message.test_id)

        response_measurements('sink', {})

    except ExperimentAbortedException as _:
        active_test_context.logger.info("Experiment was aborted")
    finally:
        active_test_context.clean_up()
        active_test_context = None
        gc.collect()


def abort_current_experiment(logger: logging.Logger):
    global active_test_context

    if active_test_context is not None:
        active_test_context.abort_or_error = True
        logger.warning(f"Request aborting the experiment")
        active_test_context.stop_event.set()
