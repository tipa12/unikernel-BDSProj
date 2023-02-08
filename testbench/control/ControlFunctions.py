import logging
import os
import queue
import re
import socket
import subprocess
import threading
import time
from typing import Callable, Union

import docker
from docker.errors import ContainerError

import launcher
from testbench.common.CustomGoogleCloudStorage import store_evaluation_in_bucket
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


def clean_up_locally(context: TestContext, p):
    context.logger.info(f"Unikernel Serial:\n {'#' * 20}\n{context.uut_serial_log}\n{'#' * 20}\n")
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


def test_boot_time(context: TestContext, image_name: str, launch_fn=launch_gcp):
    q = queue.Queue()
    udp_thread = threading.Thread(target=receive_udp_packet, args=(context, q))
    udp_thread.start()

    clean_up = launch_fn(context, image_name)
    context.instance_clean_up = clean_up

    if active_test_context.stop_event.wait(30):
        if active_test_context.is_aborted:
            raise ExperimentAbortedException()

    udp_thread.join(0.1)

    if udp_thread.is_alive():
        context.logger.error("The Unikernel did not send a boot packet in 10 seconds! Aborting the Experiment")
        raise ExperimentFailedException("Boot Packet Timeout")

    context.logger.info(f"Unikernel Booted in {context.boot_packet_timestamp} - {context.start_timestamp}s.")


active_test_context: Union[TestContext, None] = None


def launch_experiment(message: StartExperimentMessage, logger: logging.Logger):
    global active_test_context

    if active_test_context is not None:
        raise ExperimentAlreadyRunningException()

    active_test_context = TestContext(logger, message.test_id)

    try:
        image_name = ensure_image_exists(active_test_context, message)
        active_test_context.image_name = image_name
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


def get_description_from_image_name(image_name: str) -> (str, str):
    rexp = re.compile(r'(mirage|unikraft)-(filter|map|average|identity)(-\w+)?')
    matched = rexp.match(image_name)
    if not matched:
        raise ExperimentFailedException(
            f'Malformed image name "{image_name}". Please enter it according to this regex: (mirage|unikraft)-(filter|map|average|identity)(-\w+)?')

    framework, operator = str(matched.group(1)), str(matched.group(2))
    return framework, operator


def build_docker_image(control_port, control_address, source_port, source_address, sink_port, sink_address, operator,
                       github_token):
    client = docker.DockerClient()
    container = client.containers.run(
        "europe-docker.pkg.dev/bdspro/eu.gcr.io/unikraft-gcp-image-builder",
        [f"unikraft-{operator}", github_token, "-F", "-m", "x86_64", "-p", "kvm",
         "-s", f"APPTESTOPERATOR_TESTBENCH_ADDR={control_address}",
         "-s", f"APPTESTOPERATOR_TESTBENCH_PORT={control_port}",
         "-s", f"APPTESTOPERATOR_SOURCE_ADDR={source_address}",
         "-s", f"APPTESTOPERATOR_SOURCE_PORT={source_port}",
         "-s", f"APPTESTOPERATOR_DESTINATION_ADDR={sink_address}",
         "-s", f"APPTESTOPERATOR_DESTINATION_PORT={sink_port}"
         ]
    )
    container.wait()


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
                                                           sink_port, sink_address, operator, framework)
    if image is None:
        context.logger.info(f'No image was found for family "{framework}". Building new image...')

    if image is None or message.force_rebuild:
        timestr = time.strftime('%Y%m%d-%H%M%S')
        latest_image_name = f'{framework}-{operator}-{timestr}'

        if framework == 'mirage':
            subprocess.run(
                [f'mirage/build.sh', latest_image_name, github_token, '-t', 'virtio', f'--op={operator}'] + ip_addrs)
        else:
            latest_image_name = build_docker_image(context, latest_image_name, control_port, control_address,
                                                   source_port, source_address,
                                                   sink_port,
                                                   sink_address,
                                                   operator, github_token)
    else:
        latest_image_name = image.name

    return latest_image_name
