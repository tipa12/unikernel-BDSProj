import socket
import time

PORT = 8082

def handleClient(client_socket, logger):
    logger.info("Get data from client")
    begin=time.time()
    timeout=2
    while True:
        # Receive data from the client
        #if you got some data, then break after timeout
        if data and time.time()-begin > timeout:
            break
        
        #if you got no data at all, wait a little longer, twice the timeout
        elif time.time()-begin > timeout*2:
            break

        #recv something
        try:
            data = client_socket.recv(8192)
            logger.info("Received a data package!")
            if data:
                # total_data.append(data)
                #change the beginning time for measurement
                begin=time.time()
            else:
                #sleep for sometime to indicate a gap
                time.sleep(0.1)
        except:
            pass
        
        

def receiveData(messageData, logger):
    # Create a TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

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

    # Close the client and server sockets
    client_socket.close()
    server_socket.close()