import re
import sys
import warnings
from typing import Any, List, Optional

import google
import iso8601
from google.api_core.exceptions import NotFound
from google.api_core.extended_operation import ExtendedOperation
from google.cloud import compute_v1


def get_image_from_url(project: str, image_url: str) -> Optional[compute_v1.Image]:
    image_client = compute_v1.ImagesClient()
    try:
        newest_image = image_client.get(project=project, image=image_url)
        return newest_image
    except NotFound:
        return None


def encode_ip(ip: str):
    return ip.replace(".", "-")


def find_image_that_matches_configuration(control_port: int, control_address: str, source_port: int,
                                          source_address: str, sink_port: int,
                                          sink_address: str, operator: str, framework: str, tuple_format: str):
    image_client = compute_v1.ImagesClient()

    filter_by_label = " AND ".join([f"labels.{k} = \"{v}\"" for k, v in {
        'framework': framework,
        'operator': operator,
        'control_addr': encode_ip(control_address),
        'source_addr': encode_ip(source_address),
        'sink_addr': encode_ip(sink_address),
        'control_port': str(control_port),
        'source_port': str(source_port),
        'sink_port': str(sink_port),
        'tuple_format': tuple_format,
    }.items()])

    request = compute_v1.types.ListImagesRequest(mapping={
        "filter": filter_by_label,
        "project": "bdspro"
    })

    result = image_client.list(request=request)

    newest = None
    for page in result.pages:
        for image in page.items:
            if image.deprecated:
                continue

            if newest is None:
                newest = image
            current_date = iso8601.parse_date(image.creation_timestamp)
            newest_date = iso8601.parse_date(newest.creation_timestamp)
            if current_date > newest_date:
                newest = image

    return newest


def reset_vm(project: str, zone: str, instance_name: str):
    client = compute_v1.InstancesClient()
    client.reset(project=project, zone=zone, instance=instance_name)


def label_unikernel_image(project: str, image_name: str, framework: str, operator: str, control_addr: str,
                          control_port: int,
                          source_addr: str, source_port: int, sink_addr: str, sink_port: int, tuple_format: str):
    image_client = compute_v1.ImagesClient()
    image = image_client.get(project=project, image=image_name)

    labels = {
        'framework': framework,
        'operator': operator,
        'control_addr': encode_ip(control_addr),
        'source_addr': encode_ip(source_addr),
        'sink_addr': encode_ip(sink_addr),
        'control_port': str(control_port),
        'source_port': str(source_port),
        'sink_port': str(sink_port),
        'tuple_format': tuple_format,
    }

    setLabelRequest = compute_v1.types.GlobalSetLabelsRequest(mapping={
        "labels": labels,
        "label_fingerprint": image.label_fingerprint
    })

    image_client.set_labels_unary(project=project, resource=image_name,
                                  global_set_labels_request_resource=setLabelRequest)


def get_image_from_family(project: str, family: str) -> Optional[compute_v1.Image]:
    """
    Retrieve the newest image that is part of a given family in a project.
    Args:
        project: project ID or project number of the Cloud project you want to get image from.
        family: name of the image family you want to get image from.
    Returns:
        An Image object.
    """
    image_client = compute_v1.ImagesClient()
    # List of public operating system (OS) images: https://cloud.google.com/compute/docs/images/os-details
    try:
        newest_image = image_client.get_from_family(project=project, family=family)
        return newest_image
    except google.api_core.exceptions.NotFound:
        return None


def disk_from_image(
        disk_type: str,
        disk_size_gb: int,
        boot: bool,
        source_image: str,
        auto_delete: bool = True,
) -> compute_v1.AttachedDisk:
    """
    Create an AttachedDisk object to be used in VM instance creation. Uses an image as the
    source for the new disk.
    Args:
         disk_type: the type of disk you want to create. This value uses the following format:
            "zones/{zone}/diskTypes/(pd-standard|pd-ssd|pd-balanced|pd-extreme)".
            For example: "zones/us-west3-b/diskTypes/pd-ssd"
        disk_size_gb: size of the new disk in gigabytes
        boot: boolean flag indicating whether this disk should be used as a boot disk of an instance
        source_image: source image to use when creating this disk. You must have read access to this disk. This can be one
            of the publicly available images or an image from one of your projects.
            This value uses the following format: "projects/{project_name}/global/images/{image_name}"
        auto_delete: boolean flag indicating whether this disk should be deleted with the VM that uses it
    Returns:
        AttachedDisk object configured to be created using the specified image.
    """
    boot_disk = compute_v1.AttachedDisk()
    initialize_params = compute_v1.AttachedDiskInitializeParams()
    initialize_params.source_image = source_image
    initialize_params.disk_size_gb = disk_size_gb
    initialize_params.disk_type = disk_type
    boot_disk.initialize_params = initialize_params
    # Remember to set auto_delete to True if you want the disk to be deleted when you delete
    # your VM instance.
    boot_disk.auto_delete = auto_delete
    boot_disk.boot = boot
    return boot_disk


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


def create_instance(
        project_id: str,
        zone: str,
        instance_name: str,
        disks: List[compute_v1.AttachedDisk],
        machine_type: str = "e2-micro",
        network_link: str = "global/networks/default",
        subnetwork_link: str = None,
        internal_ip: str = None,
        external_access: bool = False,
        external_ipv4: str = None,
        accelerators: List[compute_v1.AcceleratorConfig] = None,
        preemptible: bool = False,
        spot: bool = False,
        instance_termination_action: str = "STOP",
        custom_hostname: str = None,
        delete_protection: bool = False,
) -> compute_v1.Instance:
    """
    Send an instance creation request to the Compute Engine API and wait for it to complete.
    Args:
        project_id: project ID or project number of the Cloud project you want to use.
        zone: name of the zone to create the instance in. For example: "us-west3-b"
        instance_name: name of the new virtual machine (VM) instance.
        disks: a list of compute_v1.AttachedDisk objects describing the disks
            you want to attach to your new instance.
        machine_type: machine type of the VM being created. This value uses the
            following format: "zones/{zone}/machineTypes/{type_name}".
            For example: "zones/europe-west3-c/machineTypes/f1-micro"
        network_link: name of the network you want the new instance to use.
            For example: "global/networks/default" represents the network
            named "default", which is created automatically for each project.
        subnetwork_link: name of the subnetwork you want the new instance to use.
            This value uses the following format:
            "regions/{region}/subnetworks/{subnetwork_name}"
        internal_ip: internal IP address you want to assign to the new instance.
            By default, a free address from the pool of available internal IP addresses of
            used subnet will be used.
        external_access: boolean flag indicating if the instance should have an external IPv4
            address assigned.
        external_ipv4: external IPv4 address to be assigned to this instance. If you specify
            an external IP address, it must live in the same region as the zone of the instance.
            This setting requires `external_access` to be set to True to work.
        accelerators: a list of AcceleratorConfig objects describing the accelerators that will
            be attached to the new instance.
        preemptible: boolean value indicating if the new instance should be preemptible
            or not. Preemptible VMs have been deprecated and you should now use Spot VMs.
        spot: boolean value indicating if the new instance should be a Spot VM or not.
        instance_termination_action: What action should be taken once a Spot VM is terminated.
            Possible values: "STOP", "DELETE"
        custom_hostname: Custom hostname of the new VM instance.
            Custom hostnames must conform to RFC 1035 requirements for valid hostnames.
        delete_protection: boolean value indicating if the new virtual machine should be
            protected against deletion or not.
    Returns:
        Instance object.
    """
    instance_client = compute_v1.InstancesClient()

    # Use the network interface provided in the network_link argument.
    network_interface = compute_v1.NetworkInterface()
    network_interface.name = network_link
    if subnetwork_link:
        network_interface.subnetwork = subnetwork_link

    if internal_ip:
        network_interface.network_i_p = internal_ip

    if external_access:
        access = compute_v1.AccessConfig()
        access.type_ = compute_v1.AccessConfig.Type.ONE_TO_ONE_NAT.name
        access.name = "External NAT"
        access.network_tier = access.NetworkTier.PREMIUM.name
        if external_ipv4:
            access.nat_i_p = external_ipv4
        network_interface.access_configs = [access]

    # Collect information into the Instance object.
    instance = compute_v1.Instance()
    instance.network_interfaces = [network_interface]
    instance.name = instance_name
    instance.disks = disks
    if re.match(r"^zones/[a-z\d\-]+/machineTypes/[a-z\d\-]+$", machine_type):
        instance.machine_type = machine_type
    else:
        instance.machine_type = f"zones/{zone}/machineTypes/{machine_type}"

    if accelerators:
        instance.guest_accelerators = accelerators

    if preemptible:
        # Set the preemptible setting
        warnings.warn(
            "Preemptible VMs are being replaced by Spot VMs.", DeprecationWarning
        )
        instance.scheduling = compute_v1.Scheduling()
        instance.scheduling.preemptible = True

    if spot:
        # Set the Spot VM setting
        instance.scheduling = compute_v1.Scheduling()
        instance.scheduling.provisioning_model = (
            compute_v1.Scheduling.ProvisioningModel.SPOT.name
        )
        instance.scheduling.instance_termination_action = instance_termination_action

    if custom_hostname is not None:
        # Set the custom hostname for the instance
        instance.hostname = custom_hostname

    if delete_protection:
        # Set the delete protection bit
        instance.deletion_protection = True

    # Prepare the request to insert an instance.
    request = compute_v1.InsertInstanceRequest()
    request.zone = zone
    request.project = project_id
    request.instance_resource = instance

    # Wait for the create operation to complete.
    print(f"Creating the {instance_name} instance in {zone}...")

    operation = instance_client.insert(request=request)

    wait_for_extended_operation(operation, "instance creation")

    print(f"Instance {instance_name} created.")
    return instance_client.get(project=project_id, zone=zone, instance=instance_name)


def create_from_custom_image(
        project_id: str, zone: str, instance_name: str, custom_image_link: str
) -> compute_v1.Instance:
    """
    Create a new VM instance with custom image used as its boot disk.
    Args:
        project_id: project ID or project number of the Cloud project you want to use.
        zone: name of the zone to create the instance in. For example: "us-west3-b"
        instance_name: name of the new virtual machine (VM) instance.
        custom_image_link: link to the custom image you want to use in the form of:
            "projects/{project_name}/global/images/{image_name}"
    Returns:
        Instance object.
    """
    disk_type = f"zones/{zone}/diskTypes/pd-standard"
    disks = [disk_from_image(disk_type, 1, True, custom_image_link, True)]
    instance = create_instance(project_id, zone, instance_name, disks)
    return instance


def delete_instance(
        project_id: str, zone: str, instance_name: str
):
    instance_client = compute_v1.InstancesClient()
    instance_client.delete(project=project_id, zone=zone, instance=instance_name)


def print_serial_output(
        project_id: str, zone: str, instance_name: str
) -> str:
    instance_client = compute_v1.InstancesClient()
    return instance_client.get_serial_port_output(project=project_id, zone=zone, instance=instance_name).contents
