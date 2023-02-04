import os

import psutil


def get_current_packet_loss() -> (int, int, int, int):
    # Call the function
    net_io_counters = psutil.net_io_counters()
    return net_io_counters.packets_sent, net_io_counters.packets_recv, net_io_counters.dropin, net_io_counters.dropout


class PacketStats:
    def __init__(self) -> None:
        super().__init__()
        self.packets_send, self.packets_received, self.packets_dropped_in, self.packets_dropped_out = \
            get_current_packet_loss()


def diff(initial: PacketStats, final: PacketStats) -> PacketStats:
    ps = PacketStats()
    ps.packets_send = final.packets_send - initial.packets_send
    ps.packets_received = final.packets_received - initial.packets_received
    ps.packets_dropped_in = final.packets_dropped_in - initial.packets_dropped_in
    ps.packets_dropped_out = final.packets_dropped_out - initial.packets_dropped_out
    return ps