import asyncio
import socket
import time


class StopWatchUDP(asyncio.DatagramProtocol):
    start = None
    path_to_unikernel_binary = "./unikernel"

    def __init__(self, path_to_unikernel_binary):
        super().__init__()
        self.path_to_unikernel_binary = path_to_unikernel_binary

    def connection_made(self, transport) -> "Used by asyncio":
        self.transport = transport

    def datagram_received(self, data, addr):
        stop = time.time()
        
        if self.start is None:
            raise "Unikernel Was never Launched"
        
        time_in_ms = (stop - self.start) * 1000
        print(f"boot time was {time_in_ms:10.5f}ms")

    async def launch_unikernel(self):
        unikernel_out = open("unikernel.log", "w")
        result = asyncio.create_subprocess_exec(self.path_to_unikernel_binary, stderr=unikernel_out)
        self.start = time.time()
        await result


async def handle_client(client, sleep_duration_in_seconds):
    loop = asyncio.get_event_loop()
    request = (await loop.sock_recv(client, 255)).decode('utf8')
    print(request)
    i = 0
    time_delta = time.time();
    while True:
        response = f"DATA{i} "
        await loop.sock_sendall(client, response.encode('utf8'))
        i += 1

        if sleep_duration_in_seconds is not None:
            await asyncio.sleep(sleep_duration_in_seconds)

        if i == 10000000:
            time_now = time.time()
            print(f"TPS: {10000000/(time.time() - time_delta)}")
            i = 0
            time_delta = time_now

    client.close()


async def tuple_generator_server(sleep_duration_in_seconds=0.002):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('localhost', 8080))
    server.listen(8)
    server.setblocking(False)

    loop = asyncio.get_event_loop()

    while True:
        client, _ = await loop.sock_accept(server)
        loop.create_task(handle_client(client, sleep_duration_in_seconds))


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    
    # Tuple Generator
    loop.create_task(tuple_generator_server(sleep_duration_in_seconds=None))

    # Boot Time
    sw = StopWatchUDP("../MirageOS/test-operator/dist/test-operator")
    t = loop.create_datagram_endpoint(lambda: sw, local_addr=('0.0.0.0', 8080))
    loop.create_task(sw.launch_unikernel())
    loop.run_until_complete(t)

    loop.run_forever()
