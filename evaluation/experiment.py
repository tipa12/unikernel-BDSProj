import datetime
import json
from typing import Optional, List
from pathlib import Path

from get_from_gcp import get_bucket, get_blobs_by_id


# class ControlMeasurements:
#     uut_serial_log: str
#     start_timestamp: float
#     start_datetime: datetime.datetime
#     boot_packet_timestamp: float
#     was_reset: bool
#
#
# class ControlData:
#     boot_packet_timestamp: float
#     start_timestamp: float
#     serial_log: str
#     measurements: [ControlMeasurements]
#
#
# class SourceData:
#     tuples_sent_timestamps: List[float]
#     number_of_tuples_sent: int
#     number_of_tuples_passing_the_filter: int
#     packets_send: int
#     packets_received: int
#     packets_dropped_in: int
#     packets_dropped_out: int
#
#
# class SinkData:
#     tuples_received_timestamps: List[float]
#     number_of_tuples_recv: int
#     packets_send: int
#     packets_received: int
#     packets_dropped_in: int
#     packets_dropped_out: int


class Experiment:

    def __init__(self, control: dict, source: dict, sink: dict) -> None:
        self.control_data = control
        self.source_data = source
        self.sink_data = sink


def load_experiment(id: str, **kwargs) -> Optional[Experiment]:
    if Path(f'{id}').exists():
        return load_from_folder(id)
    return fetch_experiment_from_gcp(id, **kwargs)


def fetch_experiment_from_gcp(id: str, **kwargs) -> Optional[Experiment]:
    project = kwargs.get('project', 'bdspro')
    bucket_name = kwargs.get('bucket', 'evaluations-1')

    bucket = get_bucket(project, bucket_name)
    if bucket is None:
        return None

    blobs = get_blobs_by_id(bucket, id)
    if not blobs:
        return None

    path = Path(f'{id}')
    path.mkdir(parents=True, exist_ok=True)

    for blob in blobs:
        file_without_id = f'{path}/{blob.name}'.split('_experiment')[0] + '.json'
        blob.download_to_filename(file_without_id)

    return load_from_folder(id)


def load_from_folder(id: str) -> Optional[Experiment]:
    path = Path(f'{id}')
    control = {}
    for file in path.iterdir():
        print(file.name)
        if 'control' in file.name:
            control = load_data_from_json(file.absolute())
        elif 'source' in file.name:
            source = load_data_from_json(file.absolute())
        elif 'sink' in file.name:
            sink = load_data_from_json(file.absolute())
    return Experiment(control, source, sink)


def load_data_from_json(file: str) -> dict:
    with open(file, 'r') as fd:
        return json.loads(fd.read())