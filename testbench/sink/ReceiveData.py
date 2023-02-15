import gc
import json
import logging
import select
import socket
import struct
import threading
import time
from datetime import datetime
from typing import Union

import testbench.common.CustomGoogleCloudStorage as gcs
from testbench.common.experiment import ExperimentAbortedException, ExperimentAlreadyRunningException, \
    ExperimentFailedException
from testbench.common.messages import ThroughputStartMessage, response_measurements, ready_for_restart, abort_experiment
from testbench.common.stats import PacketStats, diff

PORT = 8081


class Measurements:

    def __init__(self) -> None:
        super().__init__()
        self.start_timestamp: float | None = None
        self.start_datetime: datetime | None = None

        self.done_timestamp: float | None = None

        self.initial_packet_stats: PacketStats | None = None
        self.final_packet_stats: PacketStats | None = None
        self.diff_packet_stats: PacketStats | None = None

        self.tuples_processing_timestamps = []
        self.tuples_received_timestamps = []
        self.number_of_tuples_recv = 0

    def get_measurements(self) -> dict:
        return {
            "start_timestamp": self.start_timestamp,
            "start_unix_timestamp": time.mktime(self.start_datetime.timetuple()),
            "done_timestamp": self.done_timestamp,
            "tuples_received_timestamps": self.tuples_received_timestamps,
            "tuples_processing_timestamps": self.tuples_processing_timestamps,
            "number_of_tuples_recv": self.number_of_tuples_recv,
            "packets": vars(self.diff_packet_stats),
        }


class TestContext:

    def __init__(self, logger: logging.Logger, sample_rate: int, restarts: int) -> None:
        super().__init__()
        self.sink_socket: socket.socket | None = None

        self.logger = logger
        self.error_or_aborted = True
        self.was_aborted = False
        self.sample_rate = sample_rate
        self.stop_event = threading.Event()
        self.restarts = restarts
        self.measurements: [Measurements] = []
        self.current_measurement = Measurements()

    def restart(self):
        self.measurements.append(self.current_measurement)
        self.current_measurement = Measurements()

    def get_measurements(self):
        return {
            "error_or_aborted": self.error_or_aborted,
            "measurements": [m.get_measurements() for m in self.measurements]
        }

    def clean_up(self):
        if self.sink_socket is not None:
            self.sink_socket.close()


MAX_RECV_BUFFER_SIZE_IN_BYTES = 4096
TUPLE_SIZE_IN_BYTES = 20


def receive_non_blocking(context: TestContext, client_socket: socket.socket):
    repeat_if_blocking_delay = 0.000001
    counter = 0

    while True:
        try:
            data = client_socket.recv(TUPLE_SIZE_IN_BYTES * 100)
            break
        except BlockingIOError as e:
            if context.stop_event.is_set():
                raise ExperimentAbortedException()

            time_delta = context.last_time_stamp
            current = time.perf_counter()
            time_delta = current - time_delta

            if counter == 0 and time_delta > 5:
                context.last_time_stamp = current

                tuples_send_in_delta = context.current_measurement.number_of_tuples_recv - context.number_of_tuples_sent_before_last_delta
                context.number_of_tuples_sent_before_last_delta = context.current_measurement.number_of_tuples_recv
                context.logger.info(f"TPS: {tuples_send_in_delta / time_delta} over the last {time_delta}s\n")

            if counter > 30:
                context.logger.info("Receive timeout")
                data = []
                break

            counter += 1
            time.sleep(repeat_if_blocking_delay)
            repeat_if_blocking_delay *= 2
    return data


def handle_client_receiver_json(client_socket: socket.socket, context: TestContext, scale: int):
    client_socket.setblocking(False)
    time_stamp = time.perf_counter()

    context.last_time_stamp = time_stamp
    context.number_of_tuples_sent_before_last_delta = 0

    is_done = False
    overflow = ''

    while not is_done:
        if context.stop_event.is_set():
            raise ExperimentAbortedException()

        data = receive_non_blocking(context, client_socket)

        if len(data) == 0:
            break

        if len(overflow) > 0:
            data = overflow + data.decode('utf-8')
        else:
            data = data.decode('utf-8')

        dec = json.JSONDecoder()
        pos = 0
        while not pos == len(data):
            if data[pos:].startswith("DONE"):
                context.current_measurement.done_timestamp = time.perf_counter()
                client_socket.send(b"ACK")
                is_done = True
                break

            try:
                received_tuple, json_len = dec.raw_decode(data[pos:])
                pos += json_len
                valid = all(k in received_tuple for k in ("a", "b", "c", "d", "e", "ts"))
                if not valid:
                    context.logger.error(f"Invalid tuple: {received_tuple}")

                if context.current_measurement.number_of_tuples_recv % context.sample_rate == 0:
                    context.current_measurement.tuples_received_timestamps.append(time.perf_counter())
                    context.current_measurement.tuples_processing_timestamps.append(received_tuple['ts'])

                context.current_measurement.number_of_tuples_recv += 1
            except json.decoder.JSONDecodeError as e:
                raise ExperimentFailedException(f"Invalid json {e}")

        overflow = data[pos:]

    context.logger.info("Receiving Done!")


def handle_client_receiver_binary(client_socket: socket.socket, context: TestContext, scale: int):
    client_socket.setblocking(False)
    time_stamp = time.perf_counter()
    context.last_time_stamp = time_stamp
    context.number_of_tuples_sent_before_last_delta = 0
    is_done = False
    while not is_done:
        if context.stop_event.is_set():
            raise ExperimentAbortedException()

        data = receive_non_blocking(context, client_socket)

        if len(data) == 0:
            break

        if len(data) % TUPLE_SIZE_IN_BYTES != 0:
            if len(data) % TUPLE_SIZE_IN_BYTES == 4:
                context.done_timestamp = time.perf_counter()
                assert data[-4:] == b"DONE"
                client_socket.send(b"ACK")
                is_done = True

        for i in range(len(data) // TUPLE_SIZE_IN_BYTES):
            received_tuple = struct.unpack(f'!5i', data[i * TUPLE_SIZE_IN_BYTES:(i + 1) * TUPLE_SIZE_IN_BYTES])
            if context.current_measurement.number_of_tuples_recv % context.sample_rate == 0:
                context.current_measurement.tuples_received_timestamps.append(time.perf_counter())

            context.current_measurement.number_of_tuples_recv += 1

    context.logger.info("Receiving Done!")


def test_tuple_throughput_receiver(context: TestContext, scale, tuple_format: str):
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
            context.current_measurement.start_datetime = datetime.now()
            context.current_measurement.start_timestamp = time.perf_counter()
            context.logger.info(f"Receiver: Accepted a connection from {client_address}")

            context.current_measurement.initial_packet_stats = PacketStats()
            try:
                if tuple_format == 'json':
                    # Handle the client's request
                    handle_client_receiver_json(client_socket, context, scale)
                else:
                    handle_client_receiver_binary(client_socket, context, scale)
                break
            finally:
                client_socket.close()
    server_socket.close()


active_test_context: Union[TestContext, None] = None


def wait_for_restart(context: TestContext):
    ready_for_restart('sink')
    context.stop_event.wait()

    if context.was_aborted:
        raise ExperimentAbortedException()

    context.stop_event.clear()
    context.restart()


def receive_data(message: ThroughputStartMessage, logger):
    global active_test_context

    if active_test_context is not None:
        raise ExperimentAlreadyRunningException()

    try:
        active_test_context = TestContext(logger, message.sample_rate, message.restarts)
        number_of_restarts = 0
        while number_of_restarts <= active_test_context.restarts:
            if number_of_restarts > 0:
                wait_for_restart(active_test_context)

            test_tuple_throughput_receiver(active_test_context, message.iterations, message.tuple_format)
            active_test_context.current_measurement.final_packet_stats = PacketStats()

            active_test_context.current_measurement.diff_packet_stats = \
                diff(active_test_context.current_measurement.initial_packet_stats,
                     active_test_context.current_measurement.final_packet_stats)

            number_of_restarts += 1

        active_test_context.error_or_aborted = False
        gcs.store_evaluation_in_bucket(logger, active_test_context.get_measurements(), 'sink', message.test_id)

        response_measurements('sink', {})

    except ExperimentFailedException:
        active_test_context.error_or_aborted = True
        abort_experiment()
    except ExperimentAbortedException as _:
        active_test_context.logger.info("Experiment was aborted")
    finally:
        active_test_context.clean_up()
        active_test_context = None
        gc.collect()


def abort_current_experiment(logger: logging.Logger):
    global active_test_context

    if active_test_context is not None:
        active_test_context.error_or_aborted = True
        active_test_context.was_aborted = True
        logger.warning(f"Request aborting the experiment")
        active_test_context.stop_event.set()


def restart_current_experiment(logger: logging.Logger):
    global active_test_context

    if active_test_context is not None:
        logger.info(f"Restart")
        active_test_context.stop_event.set()
