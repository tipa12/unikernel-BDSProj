import socket
import struct

PORT = 8081

def handleClient(client_socket, logger):
    logger.info("Get data from client")

    tuples = []
    
    while True:
        data = client_socket.recv(20)

        tuples.append(struct.unpack('!5i', data))

        if len(data) == 0:
            # context.logger.info("Receiving Done!")
            break

        #if context.number_of_tuples_recv % scale // 10 == 0:
        #    context.tuples_received_timestamps.append(time.perf_counter())

        #context.number_of_tuples_recv += 1
    logger.info("Number of received tuples: {}".format(len(tuples)))
        

def receiveData(messageData, logger):
    try:
        # Create a TCP socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind the socket to a local address and port
        server_socket.bind(('0.0.0.0', PORT))

        # Start listening for incoming connections
        server_socket.listen()

        # Accept a single incoming connection
        client_socket, client_address = server_socket.accept()
        logger.info(f"Accepted a connection from {client_address}")
        print(f"Accepted a connection from {client_address}")

        # Handle the client's request
        handleClient(client_socket, logger)

        logger.info("Sockets will be closed")
    finally:
        # Close the client and server sockets
        client_socket.close()
        server_socket.close()