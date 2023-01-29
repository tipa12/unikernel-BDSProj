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


def handle_client(client_socket, logger: logging.Logger, data, delay, iterations):
    # Send data to the client at an increasing rate
    for tuple in data:
        # Construct the data as a tuple
        # data = (i, time.perf_counter())

        print(tuple)
        # pack the values into a byte string
        packed_data = struct.pack('!5i', *tuple)

        # Send the data to the client
        client_socket.send(packed_data)

        # Decrease the delay time - comment out to send data at a constant rate
        delay *= 0.9

        if delay < 0.001:
            continue

        time.sleep(delay)

    logger.info("Tuple Throughput done")


def test_tuple_throughput(logger: logging.Logger, data, delay, iterations=1000):
    # Create a TCP socket
    client_socket = None
    server_socket = None
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind the socket to a local address and port
        server_socket.bind(('0.0.0.0', TUPLE_SOURCE_PORT))

        # Start listening for incoming connections
        server_socket.listen()

        # Accept a single incoming connection
        client_socket, client_address = server_socket.accept()
        print(f"Accepted a connection from {client_address}")

        # Handle the client's request
        handle_client(client_socket, logger, data, delay, iterations)
    finally:
        # Close the client and server sockets
        if client_socket is not None: client_socket.close()
        if server_socket is not None: server_socket.close()


def test_gcp(image_name: str, logger: logging.Logger, data, delay):
    # boot_time_test = threading.Thread(target=test_boot_time_gcp, args=(image_name, logger))
    tuple_throughput_test = threading.Thread(target=test_tuple_throughput, args=(logger, data, delay))

    # boot_time_test.start()
    tuple_throughput_test.start()

    # boot_time_test.join(30)
    tuple_throughput_test.join(10)

    # if boot_time_test.is_alive() or tuple_throughput_test.is_alive():
    #    raise ExperimentFailedException("Timeout")
