import logging
import queue
import socket
import threading
import time
import uuid
import struct

# from dataService.launcher.gcp_launcher import create_from_custom_image

TUPLE_SOURCE_PORT = 8081

TUPLE_TARGET_PORT = 8082

BOOT_PACKAGE_PORT = 8080


class ExperimentFailedException(Exception):
    pass


def launch_gcp(image_name: str, logger: logging.Logger):
    # Send an HTTP request using the requests library
    project = 'bdspro'
    zone = 'europe-west1-b'
    test_id = uuid.uuid4()
    framework = "unikraft"

    start = time.perf_counter()
    response = create_from_custom_image(project, zone, f"{framework}-{test_id}",
                                        f"projects/bdspro/global/images/{image_name}")

    logger.info(f"GCP Instance Creation Request response:\n{response}")
    return start


def receive_udp_packet(q: queue.Queue, logger: logging.Logger):
    # Create a UDP socket and listen for incoming packets
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', BOOT_PACKAGE_PORT))
    # TODO: Verify data and addr
    data, addr = sock.recvfrom(1024)
    q.put(time.perf_counter())
    logger.debug(f"Received Boot Packet. Data = {data}, Addr = {addr}")


def test_boot_time_gcp(image_name: str, logger: logging.Logger):
    q = queue.Queue()
    udp_thread = threading.Thread(target=receive_udp_packet, args=(q, logger))
    udp_thread.start()
    start = launch_gcp(image_name, logger)
    udp_thread.join(30)
    if udp_thread.is_alive():
        logger.error("The Unikernel did not send a boot packet in 10 seconds! Aborting the Experiment")
        raise ExperimentFailedException("Boot Packet Timeout")

    stop = q.get(False)
    logger.info(f"Unikernel Booted in {stop - start}ms.")



