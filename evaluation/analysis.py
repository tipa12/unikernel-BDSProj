import numpy as np

from experiment import Experiment


def get_send_latency(experiment: Experiment):
    return np.diff(experiment.source_data.tuples_sent_timestamps)


def get_recv_latency(experiment: Experiment):
    return np.diff(experiment.sink_data.tuples_received_timestamps)


def get_number_of_dropped_tuples(experiment: Experiment):
    return experiment.sink_data.number_of_tuples_recv - experiment.source_data.number_of_tuples_passing_the_filter
