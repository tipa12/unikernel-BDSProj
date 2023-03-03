#!/usr/bin/python3
import logging
import pickle
import socket
import time
from datetime import datetime

import psutil
from google.cloud import storage


def get_current_packet_loss() -> (int, int, int, int):
    # Call the function
    net_io_counters = psutil.net_io_counters()
    return net_io_counters.packets_sent, net_io_counters.packets_recv, net_io_counters.dropin, net_io_counters.dropout


class PacketStats:
    def __init__(self) -> None:
        super().__init__()
        self.packets_send, self.packets_received, self.packets_dropped_in, self.packets_dropped_out = \
            get_current_packet_loss()

    def __str__(self) -> str:
        as_str = "PacketStats:\n"
        for k, v in vars(self).items():
            as_str += f"\t {k}: {v}"
        return as_str


def diff(initial: PacketStats, final: PacketStats) -> PacketStats:
    ps = PacketStats()
    ps.packets_send = final.packets_send - initial.packets_send
    ps.packets_received = final.packets_received - initial.packets_received
    ps.packets_dropped_in = final.packets_dropped_in - initial.packets_dropped_in
    ps.packets_dropped_out = final.packets_dropped_out - initial.packets_dropped_out
    return ps


# Set up the server
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(("0.0.0.0", 8081))
server_socket.listen(1)

delay = 0.1
ramp_factor = 1 / 1.01


def create_logger(logger_name: str):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    # Create a console handler
    console_handler = logging.StreamHandler()
    # Set the console handler level to DEBUG
    console_handler.setLevel(logging.INFO)
    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Set the formatter for the console handler
    console_handler.setFormatter(formatter)
    # Add the console handler to the logger
    logger.addHandler(console_handler)

    return logger


# Wait for a client to connect

def downloadDataset(datasetId):
    # Set up the Cloud Storage client
    projectId = "bdspro"
    client = storage.Client(project=projectId)

    # Set the name of the bucket and the file to download
    bucketName = "datasetbucket3245"
    fileName = datasetId + ".pkl"

    # Use the client to download the file
    bucket = client.bucket(bucketName)
    blob = bucket.blob(fileName)
    file = blob.download_as_string()

    # Deserialize the data from the file
    data = pickle.loads(file)

    return data


logger = create_logger("tuple_source")
data = downloadDataset('ds-20230105165324-976bcf5a-f8ef-41c3-b447-7fe8463b48f2')
iterations = 10000
while True:
    client_socket, client_address = server_socket.accept()
    initial = PacketStats()
    start_date = datetime.now()
    start_ts = int(time.perf_counter() * 1000)
    logger.info(f"Client connected from: {client_address}")
    logger.info(f"Start: {start_date}: {start_ts}")
    tuples_send = 0
    for iteration in range(iterations):
        for i in range(0, len(data)):
            tuple_data = b'{"a": %d,"b": %d,"c": %d,"d": %d,"e": %d, "f": %d}|' % (
                int(time.perf_counter() * 1000), data[i][1], data[i][2], data[i][3],
                tuples_send, data[i][0])
            client_socket.sendall(tuple_data)
            tuples_send += 1

    final = PacketStats()
    logger.info(f"{diff(initial, final)}")
    logger.info(
        f"Done: started at {time.mktime(start_date.timetuple())} ended at {time.mktime(datetime.now().timetuple())}")
    logger.info(f"Perf Counter in ms {int(time.perf_counter() * 1000) - start_ts}")
    client_socket.close()

server_socket.close()
