import errno
import logging
import queue
import socket
import subprocess
import sys
import threading
import time
import uuid
import struct

# append the path of the
# parent directory
from _socket import TCP_NODELAY
from typing import Callable

# Import from sibling directory
sys.path.append("..")
from launcher.gcp_launcher import create_from_custom_image
from launcher.gcp_launcher import delete_instance
from launcher.gcp_launcher import print_serial_output
from experiments.stats import get_current_packet_loss

TUPLE_SOURCE_PORT = 8081

TUPLE_TARGET_PORT = 8082

BOOT_PACKAGE_PORT = 8080


class TestContext:

    def __init__(self, logger: logging.Logger) -> None:
        super().__init__()
        self.test_id: uuid.UUID = uuid.uuid4()
        self.logger = logger
        logger: logging.Logger
        self.uut_serial_log: str = None
        self.source_socket: socket.socket = None
        self.boot_socket: socket.socket = None
        self.sink_socket: socket.socket = None
        self.instance_clean_up: Callable = None
        self.init_stats: (int, int, int, int)
        self.tuples_send_timestamps = []
        self.tuples_received_timestamps = []

        self.packets_during_setup = (int, int, int, int)
        self.packets_during_evaluation = (int, int, int, int)

        self.number_of_tuples_sent = 0
        self.number_of_tuples_recv = 0
        self.number_of_expected_tuples = 0

    def clean_up(self):
        if self.source_socket is not None:
            self.logger.debug("Closing Source Socket")
            self.source_socket.close()

        if self.sink_socket is not None:
            self.logger.debug("Closing Sink Socket")
            self.sink_socket.close()

        if self.boot_socket is not None:
            self.logger.debug("Closing Boot Socket")
            self.boot_socket.close()

        if self.instance_clean_up is not None:
            self.logger.debug("Cleaning Up Instance")
            self.instance_clean_up()


class ExperimentFailedException(Exception):
    pass


def launch_locally(context: TestContext, image_name: str):
    start = time.perf_counter()
    subprocess.call(["./scripts/qemu_guest.sh", "-b", "kraft0", image_name])
    return start


def clean_up_gcp(context: TestContext, project, zone, instance_name):
    context.uut_serial_log = print_serial_output(project, zone, instance_name)
    context.logger.info(f"Unikernel Serial:\n {'#' * 20}\n{context.uut_serial_log}\n{'#' * 20}\n")
    delete_instance(project, zone, instance_name)


def launch_gcp(context: TestContext, image_name: str) -> (float, Callable):
    # Send an HTTP request using the requests library
    project = 'bdspro'
    zone = 'europe-west1-b'
    framework = "unikraft"
    instance_name = f"{framework}-{context.test_id}"

    start = time.perf_counter()
    response = create_from_custom_image(project, zone, instance_name,
                                        f"projects/bdspro/global/images/{image_name}")

    return start, lambda: clean_up_gcp(context, project, zone, instance_name)


def receive_udp_packet(context: TestContext, q: queue.Queue):
    # Create a UDP socket and listen for incoming packets
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', BOOT_PACKAGE_PORT))
    context.boot_socket = sock
    # TODO: Verify data and addr
    data, addr = sock.recvfrom(1024)
    q.put(time.perf_counter())
    context.logger.debug(f"Received Boot Packet. Data = {data}, Addr = {addr}")


def test_boot_time(context: TestContext, image_name: str, launcher=launch_locally):
    q = queue.Queue()
    udp_thread = threading.Thread(target=receive_udp_packet, args=(context, q))
    udp_thread.start()

    start, clean_up = launcher(context, image_name)
    context.instance_clean_up = clean_up

    udp_thread.join(30)
    if udp_thread.is_alive():
        context.logger.error("The Unikernel did not send a boot packet in 10 seconds! Aborting the Experiment")
        raise ExperimentFailedException("Boot Packet Timeout")

    stop = q.get(False)
    context.logger.info(f"Unikernel Booted in {stop - start}s.")


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
            delay = 0.000001
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
                    time.sleep(delay)
                    delay *= 2

            context.number_of_tuples_sent += 1
            if data_tuple[0] > 0:
                if context.number_of_expected_tuples % scale // 100 == 0:
                    context.tuples_send_timestamps.append(time.perf_counter())
                context.number_of_expected_tuples += 1

            # Decrease the delay time - comment out to send data at a constant rate
            delay *= 1 / ramp_factor

            if delay < 0.0001:
                continue

            time.sleep(delay)

    print()
    context.logger.info("Sending Done")

    # make sure packets are flushed
    time.sleep(5)


def handle_client_receiver(client_socket: socket, context: TestContext, scale: int):
    while True:
        data = client_socket.recv(20)

        if len(data) == 0:
            context.logger.info("Receiving Done!")
            break

        if context.number_of_tuples_recv % scale // 10 == 0:
            context.tuples_received_timestamps.append(time.perf_counter())

        context.number_of_tuples_recv += 1


def test_tuple_throughput_receiver(context: TestContext, scale):
    # Create a TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    context.sink_socket = server_socket

    # Bind the socket to a local address and port
    server_socket.bind(('0.0.0.0', TUPLE_TARGET_PORT))

    # Start listening for incoming connections
    server_socket.listen()

    # Accept a single incoming connection
    server_socket, client_address = server_socket.accept()
    context.logger.info(f"Receiver: Accepted a connection from {client_address}")

    # Handle the client's request
    handle_client_receiver(server_socket, context, scale)


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
    server_socket.bind(('0.0.0.0', TUPLE_SOURCE_PORT))

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


def test_gcp(image_name: str, logger: logging.Logger, data, delay, scale=100, ramp_factor=1.05):
    context = TestContext(logger)
    context.logger.info(f"Starting Test: {context.test_id}")
    try:
        pre_init_pac_sent, pre_init_pac_recv, pre_init_dropin, pre_init_dropout = get_current_packet_loss()
        boot_test = threading.Thread(target=test_boot_time, args=(context, image_name, launch_gcp))
        tuple_throughput_test = threading.Thread(target=test_tuple_throughput,
                                                 args=(context, data, delay, scale, ramp_factor))
        tuple_throughput_test_receiver = threading.Thread(target=test_tuple_throughput_receiver,
                                                          args=(context, scale))

        tuple_throughput_test.start()
        tuple_throughput_test_receiver.start()
        boot_test.start()

        boot_test.join()
        tuple_throughput_test.join()
        tuple_throughput_test_receiver.join()

        fin_pac_sent, fin_pac_recv, fin_dropin, fin_dropout = get_current_packet_loss()

        context.packets_during_setup = (
            context.init_stats[0] - pre_init_pac_sent, context.init_stats[1] - pre_init_pac_recv,
            context.init_stats[2] - pre_init_dropin, context.init_stats[3] - pre_init_dropout)

        context.packets_during_evaluation = (
            fin_pac_sent - context.init_stats[0], fin_pac_recv - context.init_stats[1],
            fin_dropin - context.init_stats[2], fin_dropout - context.init_stats[3])

        logger.info(
            f"Packets Sent during setup: {context.init_stats[0] - pre_init_pac_sent} / Received: {context.init_stats[1] - pre_init_pac_recv}")

        logger.info(
            f"Packets Sent: {fin_pac_sent - context.init_stats[0]} / Received: {fin_pac_recv - context.init_stats[1]}")

        logger.info(
            f"Packet-Loss In: {fin_dropin - context.init_stats[2]} / Out: {fin_dropout - context.init_stats[3]}")

        latency_first_first = context.tuples_received_timestamps[0] - context.tuples_send_timestamps[0]

        total = context.tuples_received_timestamps[-1] - context.tuples_send_timestamps[0]

        logger.info(
            "\n".join([
                "Stats:",
                f"Number of Tuples sent: {context.number_of_tuples_sent}",
                f"Number of Tuples expected: {context.number_of_expected_tuples}",
                f"Number of Tuples received: {context.number_of_tuples_recv}",
                f"Total Time: {total}s. TPS of {context.number_of_tuples_sent / total}",
                f"First Tuple Latency: {latency_first_first}s",
            ])
        )

        if tuple_throughput_test.is_alive():
            raise ExperimentFailedException("Timeout")

        return context
    finally:
        context.clean_up()
