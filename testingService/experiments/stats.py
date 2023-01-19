import os

import psutil


def get_current_packet_loss() -> (int, int):
    # Call the function
    net_io_counters = psutil.net_io_counters()
    return net_io_counters.packets_sent, net_io_counters.packets_recv, net_io_counters.dropin, net_io_counters.dropout


