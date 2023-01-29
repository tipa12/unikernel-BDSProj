import socket
import struct
import threading
import time
import CustomGoogleCloudStorage as gcs

PORT = 8081

def handle_client(data, delay, client_socket, iterations, logger):
    lengthOfData = len(data)
    current = 0

    # Send data to the client at an increasing rate
    for iteration in range(iterations):
        tuple = data[current]
        # Construct the data as a tuple
        # data = (i, time.perf_counter())

        # pack the values into a byte string
        packed_data = struct.pack('!5i', *tuple)

        # Send the data to the client
        client_socket.send(packed_data)

        # Decrease the delay time - comment out to send data at a constant rate
        # delay *= 0.9

        #if delay < 0.001:
        #    continue
        current += 1
        if current == lengthOfData:
            current = 0

        time.sleep(delay)

    logger.info("Tuple Throughput done")


def test_tuple_throughput(data, delay, iterations, logger):
    # Create a TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to a local address and port
    server_socket.bind(('0.0.0.0', PORT))

    # Start listening for incoming connections
    server_socket.listen()

    # Accept a single incoming connection
    client_socket, client_address = server_socket.accept()
    print(f"Accepted a connection from {client_address}")

    # Handle the client's request
    handle_client(data, delay, client_socket, iterations, logger)

    # Close the client and server sockets
    client_socket.close()
    server_socket.close()


def test_gcp(data, delay, iterations, logger):
    # boot_time_test = threading.Thread(target=test_boot_time_gcp, args=(image_name, logger))
    tuple_throughput_test = threading.Thread(target=test_tuple_throughput, args=(data, delay, iterations, logger))

    # boot_time_test.start()
    tuple_throughput_test.start()

    # boot_time_test.join(30)
    tuple_throughput_test.join()

    #if boot_time_test.is_alive() or tuple_throughput_test.is_alive():
    #    raise ExperimentFailedException("Timeout")

def sendData(messageData, logger):
    if 'datasetId' not in messageData:
        logger.error("No datasetId given")
        return
    if 'delay' not in messageData:
        logger.error("No delay to send")
        return
    if 'iterations' not in messageData:
        logger.error("No iterations given")
        return
    
    datasetId = messageData['datasetId']
    delay = float(messageData['delay'])
    iterations = int(messageData['iterations'])

    data = gcs.downloadDataset(datasetId)

    test_gcp(data, delay, iterations, logger)
