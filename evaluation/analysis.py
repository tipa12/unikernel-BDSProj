import numpy as np

from experiment import Experiment


def get_send_latency(experiment: Experiment):
    return np.diff(experiment.source_data.tuples_sent_timestamps)


def get_recv_latency(experiment: Experiment):
    return np.diff(experiment.sink_data.tuples_received_timestamps)


def get_number_of_dropped_tuples(experiment: Experiment):
    return experiment.sink_data['measurements'][0]['number_of_tuples_recv'] - experiment.source_data.number_of_tuples_passing_the_filter

def p99_latency(values: [float]):
    latencies_sorted = sorted(values)  # sort the latencies
    index_p99 = int(len(values) * 0.99)
    if len(latencies_sorted) <= index_p99 + 1:
        return (latencies_sorted[-1] + latencies_sorted[-2]) / 2

    return (latencies_sorted[index_p99] + latencies_sorted[index_p99 + 1]) / 2
