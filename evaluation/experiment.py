import json
from typing import Optional, List
from pathlib import Path


from get_from_gcp import get_bucket, get_blobs_by_id


class ControlData:
    boot_packet_timestamp: float
    start_timestamp: float
    serial_log: str


class SourceData:
    tuples_sent_timestamps: List[float]
    number_of_tuples_sent: int
    number_of_tuples_passing_the_filter: int
    packets_send: int
    packets_received: int
    packets_dropped_in: int
    packets_dropped_out: int


class SinkData:
    tuples_received_timestamps: List[float]
    number_of_tuples_recv: int
    packets_send: int
    packets_received: int
    packets_dropped_in: int
    packets_dropped_out: int


class Experiment:
    
    def __init__(self, control: ControlData, source: SourceData, sink: SinkData) -> None:
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
    for file in path.iterdir():
        if 'control' in file.name:
            control = load_control_data_from_json(file.absolute())
        elif 'source' in file.name:
            source = load_source_data_from_json(file.absolute())
        elif 'sink' in file.name:
            sink = load_sink_data_from_json(file.absolute())
    return Experiment(control, source, sink)


def load_control_data_from_json(file: str) -> ControlData:
    with open(file, 'r') as fd:
        contents = json.loads(fd.read())
        control = ControlData
        control.boot_packet_timestamp = contents['boot_packet_timestamp']
        control.start_timestamp = contents['boot_packet_timestamp']
        control.serial_log = contents['serial_log']
        return control


def load_source_data_from_json(file: str) -> SourceData:
    with open(file, 'r') as fd:
        contents = json.loads(fd.read())
        source = SourceData
        print(contents)
        source.tuples_sent_timestamps = contents['tuples_sent_timestamps']
        source.number_of_tuples_sent = contents['number_of_tuples_sent']
        source.number_of_tuples_passing_the_filter = contents['number_of_tuples_passing_the_filter']
        source.packets_send = contents['packets']['packets_send']
        source.packets_received = contents['packets']['packets_received']
        source.packets_dropped_in = contents['packets']['packets_dropped_in']
        source.packets_dropped_out = contents['packets']['packets_dropped_out']
        return source


def load_sink_data_from_json(file: str) -> SinkData:
    with open(file, 'r') as fd:
        contents = json.loads(fd.read())
        sink = SinkData
        sink.tuples_received_timestamps = contents['tuples_received_timestamps']
        sink.number_of_tuples_recv = contents['number_of_tuples_recv']
        sink.packets_send = contents['packets']['packets_send']
        sink.packets_received = contents['packets']['packets_received']
        sink.packets_dropped_in = contents['packets']['packets_dropped_in']
        sink.packets_dropped_out = contents['packets']['packets_dropped_out']
        return sink
