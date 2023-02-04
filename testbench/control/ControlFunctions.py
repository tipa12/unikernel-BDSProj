import logging
import queue
import socket
import threading
import time
from typing import Callable, Union

import launcher
from testbench.common.CustomGoogleCloudStorage import store_evaluation, store_evaluation_in_bucket
from testbench.common.experiment import *
from testbench.common.messages import StartExperimentMessage, throughput_start, abort_experiment

PORT = 8081


class TestContext:

    def __init__(self, logger: logging.Logger, test_id: str) -> None:
        super().__init__()
        self.logger = logger
        logger: logging.Logger
        self.test_id = test_id

        self.boot_packet_timestamp = None
        self.start_timestamp = None

        self.stop_event: threading.Event = threading.Event()
        self.is_aborted: bool = False
        self.source_is_done: bool = False
        self.sink_is_done: bool = False

        self.uut_serial_log: str | None = None
        self.instance_clean_up: Callable = None
        self.boot_socket: socket.socket | None = None

        self.source_measurements: dict | None = None
        self.sink_measurements: dict | None = None

    def get_measurements(self) -> dict:
        return {
            "boot_packet_timestamp": self.boot_packet_timestamp,
            "start_timestamp": self.start_timestamp,
            "serial_log": self.uut_serial_log,
            "source_measurements": self.source_measurements,
            "sink_measurements": self.sink_measurements,
        }

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
    instance_name = f"{framework}-{context.test_id[len('experiment_2023-02-04T15-57-46-'):]}"

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

    if active_test_context.stop_event.wait(30):
        if active_test_context.is_aborted:
            raise ExperimentAbortedException()

    udp_thread.join(0.1)

    if udp_thread.is_alive():
        context.logger.error("The Unikernel did not send a boot packet in 10 seconds! Aborting the Experiment")
        raise ExperimentFailedException("Boot Packet Timeout")

    context.logger.info(f"Unikernel Booted in {context.boot_packet_timestamp - context.start_timestamp}s.")


active_test_context: Union[TestContext, None] = None


def launch_experiment(message: StartExperimentMessage, logger: logging.Logger):
    global active_test_context

    if active_test_context is not None:
        raise ExperimentAlreadyRunningException()

    active_test_context = TestContext(logger, message.test_id)

    try:
        image_name = message.image_name  # 'unikraft-1675005257' #unikraft-1674828757, unikraft-1675000514
        # TODO: Test if image Exists and build if necessary

        throughput_start(message.test_id, message.iterations, message.delay, message.ramp_factor, message.dataset_id)

        # deploy unikernel on google cloud
        boot_test = test_boot_time(active_test_context, image_name)
        active_test_context.stop_event.wait()
        if active_test_context.is_aborted:
            raise ExperimentAbortedException()
        else:
            assert active_test_context.source_is_done and active_test_context.sink_is_done

            # TODO: Hacky that the instance_clean_up method fetches the serial_logs, but clean up is called in the
            #       finally block
            active_test_context.instance_clean_up()
            active_test_context.instance_clean_up = lambda: None

            store_evaluation_in_bucket(logger, active_test_context.get_measurements(), active_test_context.test_id)
            logger.info("Experiment is Done!")

    except ExperimentFailedException as e:
        # Notify source and sink
        abort_experiment()
        logger.error(e)
    except ExperimentAbortedException as e:
        logger.info("Experiment was aborted")
    finally:
        active_test_context.instance_clean_up()
        active_test_context = None


def abort_current_experiment(logger: logging.Logger):
    global active_test_context

    if active_test_context is not None:
        logger.warning(f"Experiment was aborted")
        active_test_context.is_aborted = True
        active_test_context.stop_event.set()


def source_is_done(source_measurements: dict):
    if active_test_context is not None:
        active_test_context.source_is_done = True
        active_test_context.source_measurements = source_measurements

    if active_test_context.sink_is_done:
        active_test_context.stop_event.set()


def sink_is_done(sink_measurements: dict):
    if active_test_context is not None:
        active_test_context.sink_is_done = True
        active_test_context.sink_measurements = sink_measurements

    if active_test_context.source_is_done:
        active_test_context.stop_event.set()
