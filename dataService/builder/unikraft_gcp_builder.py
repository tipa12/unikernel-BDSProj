import logging
import os.path
import subprocess
import sys
import tempfile
import uuid
from typing import Any

import google.cloud.storage
import docker

# Create a Docker client
from google.api_core.extended_operation import ExtendedOperation
from google.cloud import compute_v1

UNIKRAFT_UNIKERNEL_REPOSITORY = 'https://github.com/ls-1801/Unikraft-Test-Operator.git'
docker_client = docker.DockerClient()


def wait_for_extended_operation(
        operation: ExtendedOperation, verbose_name: str = "operation", timeout: int = 300
) -> Any:
    """
    This method will wait for the extended (long-running) operation to
    complete. If the operation is successful, it will return its result.
    If the operation ends with an error, an exception will be raised.
    If there were any warnings during the execution of the operation
    they will be printed to sys.stderr.

    Args:
        operation: a long-running operation you want to wait on.
        verbose_name: (optional) a more verbose name of the operation,
            used only during error and warning reporting.
        timeout: how long (in seconds) to wait for operation to finish.
            If None, wait indefinitely.

    Returns:
        Whatever the operation.result() returns.

    Raises:
        This method will raise the exception received from `operation.exception()`
        or RuntimeError if there is no exception set, but there is an `error_code`
        set for the `operation`.

        In case of an operation taking longer than `timeout` seconds to complete,
        a `concurrent.futures.TimeoutError` will be raised.
    """
    result = operation.result(timeout=timeout)

    if operation.error_code:
        print(
            f"Error during {verbose_name}: [Code: {operation.error_code}]: {operation.error_message}",
            file=sys.stderr,
            flush=True,
        )
        print(f"Operation ID: {operation.name}", file=sys.stderr, flush=True)
        raise operation.exception() or RuntimeError(operation.error_message)

    if operation.warnings:
        print(f"Warnings during {verbose_name}:\n", file=sys.stderr, flush=True)
        for warning in operation.warnings:
            print(f" - {warning.code}: {warning.message}", file=sys.stderr, flush=True)

    return result


def create_disk_from_google_cloud_bucket(logger: logging.Logger, blob_url: str, image_name: str):
    # Create a client
    image_client = compute_v1.ImagesClient()
    image = compute_v1.Image()
    image.source_url = blob_url
    image.storage_location = ['europe-west1-b']
    image.name = image_name

    operation = image_client.insert(project="bdspro", image_resource=image)

    wait_for_extended_operation(operation, "image creation from disk")

    return image_client.get(project="bdspro", image=image_name)


def setup_unikraft_image_for_gce(logger: logging.Logger, revision=None):
    temp_dir = build_unikraft(logger, revision)
    image_name = build_raw_image(logger, temp_dir)
    blob_url = upload_to_google_cloud_bucket(logger, temp_dir, image_name)
    create_disk_from_google_cloud_bucket(logger, blob_url, image_name)


def ensure_image_is_present(logger: logging.Logger):
    try:
        docker_client.images.get('europe-docker.pkg.dev/bdspro/eu.gcr.io/unikraft-builder')
        logger.info("Image is Present")
    except Exception:
        logger.info("Image is not Present")
        subprocess.run(['gcloud', 'auth', 'configure-docker', 'europe-docker.pkg.dev'])
        logger.info("Configured docker")
        docker_client.images.pull('europe-docker.pkg.dev/bdspro/eu.gcr.io/unikraft-builder')
        logger.info("pulled image")


def build_unikraft(logger: logging.Logger, revision=None) -> str:
    ensure_image_is_present(logger)
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()

    logger.info(f"Clone Git Repo: {UNIKRAFT_UNIKERNEL_REPOSITORY}")
    # Clone the Git repository into the temporary directory
    subprocess.run(['git', 'clone', UNIKRAFT_UNIKERNEL_REPOSITORY, temp_dir])

    if revision is not None:
        subprocess.run(['git', 'checkout', revision], cwd=temp_dir)

    # Launch Docker Unikraft Builder
    container = docker_client.containers.create(
        image='europe-docker.pkg.dev/bdspro/eu.gcr.io/unikraft-builder',
        volumes={
            temp_dir: {'bind': '/home/appuser/scripts/workdir/apps/app-httpreply', 'mode': 'rw'}
        }
    )
    subprocess.run(['chmod', '-R', "757", temp_dir])
    logger.info(f"Launching Container")
    container.start()
    exit_code = container.wait()
    logger.info(f"Container Stopped: {exit_code}")
    return temp_dir


def build_raw_image(logger: logging.Logger, temp_dir: str) -> str:
    image_name = f'unikraft-{uuid.uuid4()}.tar.gz'
    subprocess.run(
        ['solo5-virtio-mkimage.sh', '-d', '-f', 'tar', '--', image_name, './build/testoperator_kvm-x86_64'],
        cwd=temp_dir)
    return image_name


def upload_to_google_cloud_bucket(logger: logging.Logger, temp_dir: str, file_name: str) -> str:
    client = google.cloud.storage.Client()
    # Get a reference to the bucket
    bucket = client.get_bucket('unikraft')
    # Create a blob in the bucket
    blob = bucket.blob(file_name)
    # Copy the file to the blob
    blob.upload_from_filename(os.path.join(temp_dir, file_name))
    return blob.public_url
