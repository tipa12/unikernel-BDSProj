import datetime
import logging
import os
import re
import socket
import subprocess
import threading
import time
from typing import Callable, Union, Tuple

import docker
from docker.errors import ContainerError

import launcher
from testbench.common.CustomGoogleCloudStorage import store_evaluation_in_bucket
from testbench.common.experiment import *
from testbench.common.messages import StartExperimentMessage, throughput_start, abort_experiment, restart_experiment

PORT = 8081


class Measurements:

    def __init__(self, was_reset: bool) -> None:
        super().__init__()
        self.uut_serial_log = None
        self.start_timestamp = None
        self.start_datetime = None
        self.boot_packet_timestamp = None
        self.was_reset = was_reset

    def get_measurements(self) -> dict:
        return {
            "was_reset": self.was_reset,
            "boot_packet_timestamp": self.boot_packet_timestamp,
            "start_unix_timestamp": time.mktime(self.start_datetime.timetuple()),
            "start_timestamp": self.start_timestamp,
            "serial_log": self.uut_serial_log,
        }


class TestContext:

    def __init__(self, logger: logging.Logger, message: StartExperimentMessage, test_id: str) -> None:
        super().__init__()
        self.image_name = None
        self.instance_name = None
        self.boot_socket: socket.socket | None = None
        self.logger = logger
        logger: logging.Logger
        self.test_id = test_id

        self.stop_event: threading.Event = threading.Event()
        self.is_aborted: bool = False
        self.source_is_done: bool = False
        self.source_waits_for_restart: bool = False
        self.sink_is_done: bool = False
        self.sink_waits_for_restart: bool = False

        self.instance_clean_up: Callable = lambda: None
        self.instance_get_serial: Callable = lambda: None

        self.configuration: StartExperimentMessage = message

        self.measurements: [Measurements] = []
        self.current_measurement = Measurements(False)

    def restart(self):
        self.measurements.append(self.current_measurement)
        self.current_measurement.uut_serial_log = self.instance_get_serial()
        self.current_measurement = Measurements(True)
        self.source_waits_for_restart = False
        self.sink_waits_for_restart = False

    def get_measurements(self) -> dict:
        return {
            "measurements": [m.get_measurements() for m in self.measurements],
            "configuration": vars(self.configuration),
            "image_name": self.image_name
        }

    def clean_up(self):
        if self.boot_socket is not None:
            self.logger.debug("Closing Boot Socket")
            self.boot_socket.close()

        if self.instance_clean_up is not None:
            self.logger.debug("Cleaning Up Instance")
            self.instance_clean_up()


def clean_up_gcp(context: TestContext, project, zone, instance_name):
    try:
        launcher.delete_instance(project, zone, instance_name)
    except Exception as e:
        context.logger.error(e)


def get_serial_gcp(context: TestContext, project, zone, instance_name):
    serial = launcher.print_serial_output(project, zone, instance_name)
    context.logger.info(f"Unikernel Serial:\n {'#' * 20}\n{serial}\n{'#' * 20}\n")

    return serial


def clean_up_locally(context: TestContext, p):
    context.logger.info(f"Unikernel Serial:\n {'#' * 20}\n{context.current_measurement.uut_serial_log}\n{'#' * 20}\n")
    p.terminate()


def wait_for_serial_socket_to_exist(file_path: str, timeout: int) -> bool:
    start_time = time.time()
    while not os.path.exists(file_path):
        time.sleep(0.1)
        if time.time() - start_time > timeout:
            return False
    else:
        return True


def read_serial_socket(context: TestContext, socket_name: str):
    context.logger.info(f"Waiting for socket: {socket_name}")
    with open("/tmp/socat.out", "w+") as file:
        p = subprocess.run(
            ["sudo", "-A", 'socat', '-', f'UNIX-CONNECT:{socket_name}'],
            stdout=file
        )


def launch_locally(context: TestContext, image_name: str) -> Callable:
    import subprocess
    p = subprocess.Popen(
        ['sudo', '-A', '/home/ls/Uni/WiSe2223/DBPRO/Unikraft-Test-Operator/scripts/qemu_guest.sh', '-x', '-b', 'kraft0',
         '-k',
         '/home/ls/Uni/WiSe2223/DBPRO/Unikraft-Test-Operator/build/testoperator_kvm-x86_64'], stdout=subprocess.PIPE)

    socket_name = ""
    while True:
        line = p.stdout.readline().decode().strip()
        print(line)
        if not line:
            break
        if line.startswith("Serial socket:"):
            socket_name = line.split(":")[1].strip()
            break

    threading.Thread(target=read_serial_socket, args=(context, socket_name)).start()

    return lambda: clean_up_locally(context, p)


def launch_gcp(context: TestContext) -> Callable:
    context.logger.info("Lauchning VM")
    # Send an HTTP request using the requests library
    project = 'bdspro'
    zone = 'europe-west1-b'
    framework = "unikraft"
    instance_name = f"{framework}-{context.test_id[len('experiment_2023-02-04T15-57-46-'):]}"
    context.instance_name = instance_name

    context.start_timestamp = time.perf_counter()
    response = launcher.create_from_custom_image(project, zone, instance_name,
                                                 f"projects/bdspro/global/images/{context.image_name}")

    return lambda: clean_up_gcp(context, project, zone, instance_name)


def receive_udp_packet(context: TestContext):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Create a UDP socket and listen for incoming packets
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', PORT))
        context.boot_socket = sock
        # TODO: Verify data and addr
        data, addr = sock.recvfrom(1024)
        context.current_measurement.boot_packet_timestamp = time.perf_counter()
        context.logger.debug(f"Received Boot Packet. Data = {data}, Addr = {addr}")
    finally:
        sock.close()


def restart_gcp(context: TestContext):
    try:
        context.logger.info("Resetting Instance")
        launcher.reset_vm('bdspro', 'europe-west1-b', context.instance_name)
    except Exception as e:
        context.logger.error(f"Problem when resetting VM: {e}")
        raise ExperimentFailedException("Problem when resetting VM")


def wait_for_unikernel_to_boot_with_timeout(timeout_in_seconds: int, thread: threading.Thread) -> bool:
    time_left = float(timeout_in_seconds)

    while time_left > 0:
        if active_test_context.stop_event.wait(10):
            if active_test_context.is_aborted:
                raise ExperimentAbortedException()
        thread.join(0.1)
        if thread.is_alive():
            time_left -= 0.1
        else:
            return True
    return False


def restart_unikernel(context: TestContext, reset_fn=restart_gcp):
    udp_thread = threading.Thread(target=receive_udp_packet, args=(context,))
    udp_thread.start()

    context.current_measurement.start_datetime = datetime.datetime.now()
    context.current_measurement.start_timestamp = time.perf_counter()
    reset_fn(context)

    if not wait_for_unikernel_to_boot_with_timeout(10, udp_thread):
        context.logger.error("The Unikernel did not send a boot packet in 10 seconds! Aborting the Experiment")
        raise ExperimentFailedException("Boot Packet Timeout")

    context.logger.info(
        f"Unikernel Booted in {context.current_measurement.boot_packet_timestamp} - {context.current_measurement.start_timestamp}s.")


def test_boot_time(context: TestContext, launch_fn=launch_gcp):
    udp_thread = threading.Thread(target=receive_udp_packet, args=(context,))
    udp_thread.start()

    context.current_measurement.start_datetime = datetime.datetime.now()
    context.current_measurement.start_timestamp = time.perf_counter()

    clean_up = launch_fn(context)

    context.instance_get_serial = lambda: get_serial_gcp(context, 'bdspro', 'europe-west1-b', context.instance_name)
    context.instance_clean_up = clean_up

    if not wait_for_unikernel_to_boot_with_timeout(20, udp_thread):
        context.logger.error("The Unikernel did not send a boot packet in 20 seconds! Aborting the Experiment")
        raise ExperimentFailedException("Boot Packet Timeout")

    context.logger.info(
        f"Unikernel Booted in {context.current_measurement.boot_packet_timestamp} - {context.current_measurement.start_timestamp}s.")


active_test_context: Union[TestContext, None] = None


def wait_for_restart(context: TestContext):
    context.logger.info("Waiting for Source and Sink to prepare for restart")
    context.stop_event.wait()

    if context.is_aborted:
        raise ExperimentAbortedException()
    elif context.sink_waits_for_restart and context.source_waits_for_restart:
        context.stop_event.clear()
        context.restart()
    else:
        raise ExperimentFailedException("Expected Source and Sink to Notify when ready for next reset")

    context.logger.info("Ready for restart")
    restart_experiment()


def launch_experiment(message: StartExperimentMessage, logger: logging.Logger):
    global active_test_context

    if active_test_context is not None:
        raise ExperimentAlreadyRunningException()

    try:
        active_test_context = TestContext(logger, message, message.test_id)
        image_name = ensure_image_exists(active_test_context, message)
        active_test_context.image_name = image_name
        number_of_restarts = 0

        # Launch initial experiment
        throughput_start(message.test_id, message.iterations, message.delay, message.ramp_factor,
                         message.dataset_id, message.sample_rate, message.restarts, message.tuple_format)

        test_boot_time(active_test_context)

        while number_of_restarts < message.restarts:
            wait_for_restart(active_test_context)
            restart_unikernel(active_test_context)
            number_of_restarts += 1

        active_test_context.restart()
        active_test_context.logger.info("Wait for source and sink to stop")
        # Wait for source and sink to save results
        active_test_context.stop_event.wait()
        if active_test_context.is_aborted:
            raise ExperimentAbortedException()
        else:
            assert active_test_context.source_is_done and active_test_context.sink_is_done

            store_evaluation_in_bucket(logger, active_test_context.get_measurements(), 'control',
                                       active_test_context.test_id)
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
    global active_test_context
    if active_test_context is not None:
        active_test_context.source_is_done = True
        active_test_context.source_measurements = source_measurements

    if active_test_context.sink_is_done:
        active_test_context.stop_event.set()


def sink_is_done(sink_measurements: dict):
    global active_test_context
    if active_test_context is not None:
        active_test_context.sink_is_done = True
        active_test_context.sink_measurements = sink_measurements

    if active_test_context.source_is_done:
        active_test_context.stop_event.set()


def get_description_from_image_name(image_name: str) -> Tuple[str, str]:
    rexp = re.compile(r'(mirage|unikraft)-(filter|map|average|identity)(-\w+)?')
    matched = rexp.match(image_name)
    if not matched:
        raise ExperimentFailedException(
            f'Malformed image name "{image_name}". Please enter it according to this regex: (mirage|unikraft)-(filter|map|average|identity)(-\w+)?')

    framework, operator = str(matched.group(1)), str(matched.group(2))
    return framework, operator


def build_unikraft_docker_image(context: TestContext, control_port, control_address, source_port,
                                source_address, sink_port,
                                sink_address, operator,
                                github_token,
                                tuple_format: str):
    # TODO: Support Tuple format for Unikraft
    client = docker.DockerClient()
    try:
        context.logger.info("Launching docker build for unikraft")
        binary_file_name = client.containers.run(
            "europe-docker.pkg.dev/bdspro/eu.gcr.io/unikraft-gcp-image-builder",
            [github_token, "-F", "-m", "x86_64", "-p", "kvm",
             "-s", f"APPTESTOPERATOR_TESTBENCH_ADDR={control_address}",
             "-s", f"APPTESTOPERATOR_TESTBENCH_PORT={control_port}",
             "-s", f"APPTESTOPERATOR_SOURCE_ADDR={source_address}",
             "-s", f"APPTESTOPERATOR_SOURCE_PORT={source_port}",
             "-s", f"APPTESTOPERATOR_DESTINATION_ADDR={sink_address}",
             "-s", f"APPTESTOPERATOR_DESTINATION_PORT={sink_port}"
             ]
        ).decode('utf-8').strip()

        context.logger.info(f"Compilation Done building Google Compute Image: {binary_file_name}")

        image_name = client.containers.run(
            "europe-docker.pkg.dev/bdspro/eu.gcr.io/virtio-mkimage",
            [binary_file_name]
        ).decode('utf-8').strip()

        context.logger.info(f"Image: {image_name} was created. Labeling the Image")
        launcher.label_unikernel_image('bdspro', image_name, 'unikraft', operator, control_address, control_port,
                                       source_address, source_port, sink_address, sink_port, tuple_format)
        context.logger.info(f"Labeling done")

        return image_name
    except ContainerError as e:
        context.logger.error(e)
        raise ExperimentFailedException("Cannot build unikraft image")


def build_mirage_docker_image(ip_addrs, operator, github_token):
    client = docker.DockerClient()

    # TODO: Florian make sure the docker build returns the image_name
    image_name = client.containers.run(
        "europe-docker.pkg.dev/bdspro/eu.gcr.io/mirageos-gcp-image-builder",
        [f"mirage-{operator}", github_token, "-u", "-t", "virtio", f"--op={operator}"] + ip_addrs,
    ).encode('utf-8').strip()

    # TODO: Florian label the image

    # launcher.label_unikernel_image('bdspro', image_name, 'unikraft', operator, , control_port,
    #                                source_address, source_port, sink_address, sink_port)
    return image_name


def ensure_image_exists(context: TestContext, message: StartExperimentMessage) -> str:
    image_name = message.image_name
    github_token = message.github_token
    operator = message.operator

    ip_addrs = []
    source_address = message.source_address
    source_port = message.source_port
    if source_address is not None and source_port is not None:
        ip_addrs += [f'--source-address={source_address}', f'--source-port={source_port}']

    sink_address = message.sink_address
    sink_port = message.sink_port
    if sink_address is not None and sink_port is not None:
        ip_addrs += [f'--sink-address={sink_address}', f'--sink-port={sink_port}']

    control_address = message.control_address
    control_port = message.control_port
    if control_address is not None and control_port is not None:
        ip_addrs += [f'--control-address={control_address}', f'--control-port={control_port}']

    framework, operator = get_description_from_image_name(image_name)

    image = launcher.find_image_that_matches_configuration(control_port, control_address, source_port, source_address,
                                                           sink_port, sink_address, operator, framework,
                                                           message.tuple_format)

    if image is None or message.force_rebuild:
        timestr = time.strftime('%y%m%d-%H%M%S')
        # image names are limited to 19 characters
        latest_image_name = f'{framework[0]}-{operator[0]}-{timestr[2:]}'

        if image is None:
            context.logger.info(f'No image was found for family "{framework}". Building new image...')

        if message.force_rebuild:
            context.logger.info(f'Force Rebuild. Building new image...')

        if framework == 'mirage':
            latest_image_name = build_mirage_docker_image(ip_addrs, operator, github_token)
        else:
            latest_image_name = build_unikraft_docker_image(context, control_port, control_address,
                                                            source_port, source_address,
                                                            sink_port,
                                                            sink_address,
                                                            operator, github_token, message.tuple_format)
    else:
        latest_image_name = image.name

    return latest_image_name


def ready_for_restart(source_or_sink):
    global active_test_context
    if active_test_context is not None:
        if source_or_sink == "source":
            active_test_context.source_waits_for_restart = True
        if source_or_sink == "sink":
            active_test_context.sink_waits_for_restart = True

    if active_test_context.source_waits_for_restart and active_test_context.sink_waits_for_restart:
        active_test_context.stop_event.set()
