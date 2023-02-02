import logging
import socket
import struct
import threading
import time

from common.experiment import ExperimentAbortedException, ExperimentAlreadyRunningException
from common.stats import PacketStats

PORT = 8081


class TestContext:

    def __init__(self, logger: logging.Logger) -> None:
        super().__init__()

        self.source_socket: socket.socket | None = None
        self.initial_packet_stats: PacketStats | None = None
        self.final_packet_stats: PacketStats | None = None
        self.diff_packet_stats: PacketStats | None = None

        self.tuples_received_timestamps = []
        self.tuple_ids_received = []
        self.number_of_tuples_recv = 0

        self.logger = logger

        self.stop_event = threading.Event()

    def clean_up(self):
        if self.source_socket is not None:
            self.source_socket.close()


global active_test_context


def handle_client_receiver(client_socket: socket, context: TestContext, scale: int):
    while True:
        if context.stop_event.is_set():
            raise ExperimentAbortedException()

        # TODO: Nonblocking

        data = client_socket.recv(20)
        received_tuple = struct.unpack('!5i', data)

        if len(data) == 0:
            context.logger.info("Receiving Done!")
            break

        context.tuple_ids_received.append(received_tuple[1])

        if context.number_of_tuples_recv % scale // 10 == 0:
            context.tuples_received_timestamps.append(time.perf_counter())

        context.number_of_tuples_recv += 1


def test_tuple_throughput_receiver(context: TestContext, scale):
    # Create a TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    context.sink_socket = server_socket

    # Bind the socket to a local address and port
    server_socket.bind(('0.0.0.0', PORT))

    # Start listening for incoming connections
    server_socket.listen()

    # Accept a single incoming connection
    server_socket, client_address = server_socket.accept()
    context.logger.info(f"Receiver: Accepted a connection from {client_address}")

    # Handle the client's request
    handle_client_receiver(server_socket, context, scale)


def receive_data(message_data, logger):
    global active_test_context

    if active_test_context is not None:
        raise ExperimentAlreadyRunningException()

    active_test_context = TestContext(logger)

    if 'iterations' not in message_data:
        logger.error("No iterations given")
        return

    iterations = int(message_data['iterations'])

    try:
        test_tuple_throughput_receiver(active_test_context, scale=int(iterations))

    finally:
        active_test_context.clean_up()
        active_test_context = None


def abort_current_experiment():
    global active_test_context

    if active_test_context is not None:
        active_test_context.stop_event.set()
