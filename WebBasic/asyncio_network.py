"""
研究 asyncio 提供的网络编程抽象组件。
主要有如下2个层次：
- Transport/Protocol
- StreamReader/StreamWriter
"""
from typing import TYPE_CHECKING
import asyncio
from asyncio import Task, Future, Event, EventLoop, Server
from asyncio import Transport, DatagramTransport, Protocol, DatagramProtocol, StreamReader, StreamWriter


# -------------------------- Transport + Protocol 使用 --------------------------------
class ProtocolEchoServer(Protocol):
    def connection_made(self, transport: Transport):
        self.transport = transport
        peername = transport.get_extra_info('peername')
        print(f"Connection from {peername}")

    def data_received(self, data):
        message = data.decode()
        print(f"Received: {message}")
        # 回显数据
        self.transport.write(data)

    def connection_lost(self, exc):
        if exc:
            print("Connection lost due to error")
        else:
            print("Connection closed")


class ProtocolEchoClient(Protocol):
    def __init__(self, message, on_con_lost):
        self.message = message
        self.on_con_lost = on_con_lost

    def connection_made(self, transport: Transport):
        self.transport = transport
        print(f"Send: {self.message}")
        self.transport.write(self.message.encode())

    def data_received(self, data):
        print(f"Received: {data.decode()}")
        self.transport.close()  # 收到回复后关闭

    def connection_lost(self, exc):
        print("Connection closed")
        self.on_con_lost.set_result(True)


async def run_protocol_echo_server():
    loop = asyncio.get_running_loop()
    server = await loop.create_server(
        lambda: ProtocolEchoServer(),
        '127.0.0.1', 8888
    )
    print("Server listening on 127.0.0.1:8888")
    async with server:
        await server.serve_forever()


async def run_protocol_echo_client():
    loop = asyncio.get_running_loop()
    on_con_lost = loop.create_future()
    transport, protocol = await loop.create_connection(
        lambda: ProtocolEchoClient("Hello Server!", on_con_lost),
        '127.0.0.1', 8888
    )

    try:
        await on_con_lost
    finally:
        transport.close()


# -------------------------- StreamReader + StreamWriter 使用 --------------------------------
async def stream_echo_server(reader: StreamReader, writer: StreamWriter):
    addr = writer.get_extra_info('peername')
    print(f"Client connected: {addr}")

    try:
        while True:
            data = await reader.readline()  # 读一行
            if not data:  # 客户端关闭连接
                break
            message = data.decode().strip()
            print(f"Received from {addr}: {message}")

            # 回显
            writer.write(data)
            await writer.drain()
    except Exception as e:
        print(f"Error with {addr}: {e}")
    finally:
        print(f"Close connection from {addr}")
        writer.close()
        await writer.wait_closed()


async def stream_echo_client():
    # 连接到服务器
    reader, writer = await asyncio.open_connection('127.0.0.1', 8888)

    message = "Hello Server!"
    print(f"Send: {message}")
    writer.write(message.encode())
    await writer.drain()  # 刷新缓冲区

    # 接收回复
    data = await reader.readline()  # 或 read(100), readuntil(b'\n') 等
    print(f"Received: {data.decode().strip()}")

    writer.close()
    await writer.wait_closed()


async def run_stream_echo_server():
    server = await asyncio.start_server(
        stream_echo_server,
        '127.0.0.1', 8888
    )
    print("Server listening on 127.0.0.1:8888")
    async with server:
        await server.serve_forever()



def main():
    run_protocol_echo_server()
    run_protocol_echo_client()
    run_stream_echo_server()
    asyncio.run(stream_echo_client())


if __name__ == "__main__":
    main()
