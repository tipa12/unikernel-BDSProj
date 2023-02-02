import logging
import queue
import threading
import time
import uuid

import common
import socket
from typing import Callable

import launcher

PORT = 8081


class TestContext:

    def __init__(self, logger: logging.Logger) -> None:
        super().__init__()
        self.logger = logger
        logger: logging.Logger
        self.test_id = uuid.uuid4()

        self.boot_packet_timestamp = None
        self.start_timestamp = None

        self.uut_serial_log: str | None = None
        self.instance_clean_up: Callable = None
        self.boot_socket: socket.socket | None = None

    def clean_up(self):
        if self.boot_socket is not None:
            self.logger.debug("Closing Boot Socket")
            self.boot_socket.close()

        if self.instance_clean_up is not None:
            self.logger.debug("Cleaning Up Instance")
            self.instance_clean_up()


def clean_up_gcp(context: TestContext, project, zone, instance_name):
    context.uut_serial_log = launcher.print_serial_output(project, zone, instance_name)
    context.logger.info(f"Unikernel Serial:\n {'#' * 20}\n{context.uut_serial_log}\n{'#' * 20}\n")
    launcher.delete_instance(project, zone, instance_name)


def launch_gcp(context: TestContext, image_name: str) -> Callable:
    # Send an HTTP request using the requests library
    project = 'bdspro'
    zone = 'europe-west1-b'
    framework = "unikraft"
    instance_name = f"{framework}-{context.test_id}"

    context.start_timestamp = time.perf_counter()
    response = launcher.create_from_custom_image(project, zone, instance_name,
                                                 f"projects/bdspro/global/images/{image_name}")

    return lambda: clean_up_gcp(context, project, zone, instance_name)


def receive_udp_packet(context: TestContext, q: queue.Queue):
    # Create a UDP socket and listen for incoming packets
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', PORT))
    context.boot_socket = sock
    # TODO: Verify data and addr
    data, addr = sock.recvfrom(1024)
    context.boot_packet_timestamp = time.perf_counter()
    context.logger.debug(f"Received Boot Packet. Data = {data}, Addr = {addr}")


def test_boot_time(context: TestContext, image_name: str):
    q = queue.Queue()
    udp_thread = threading.Thread(target=receive_udp_packet, args=(context, q))
    udp_thread.start()

    clean_up = launch_gcp(context, image_name)
    context.instance_clean_up = clean_up

    udp_thread.join(30)
    if udp_thread.is_alive():
        context.logger.error("The Unikernel did not send a boot packet in 10 seconds! Aborting the Experiment")
        raise common.ExperimentFailedException("Boot Packet Timeout")

    context.logger.info(f"Unikernel Booted in {context.boot_packet_timestamp - context.start_timestamp}s.")


global active_test_context


def start_experiment(message, logger: logging.Logger):
    global active_test_context

    if active_test_context is not None:
        raise common.ExperimentAlreadyRunningException()

    active_test_context = TestContext(logger)

    try:
        image_name = message['imageName']  # 'unikraft-1675005257' #unikraft-1674828757, unikraft-1675000514

        # deploy unikernel on google cloud
        boot_test = test_boot_time(active_test_context, image_name)

    except common.ExperimentFailedException as e:
        # TODO: abort the experiment
        logger.error(e)
    except common.ExperimentAbortedException as e:
        logger.info("Experiment was aborted")
    finally:
        active_test_context.instance_clean_up()
        active_test_context = None
