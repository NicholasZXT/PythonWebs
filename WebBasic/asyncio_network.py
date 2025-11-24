"""
研究 asyncio 提供的网络编程抽象组件。
主要有如下2个层次：
- Transport/Protocol
- StreamReader/StreamWriter

Transport/Protocol 需要配合 AbstractEventLoop 提供的 create_server()、create_connection() 方法使用。

StreamReader/StreamWriter 需要配合 start_server(), open_connection() 函数使用。
"""
from typing import TYPE_CHECKING
import asyncio
from asyncio import AbstractEventLoop, AbstractServer, BaseEventLoop, Server, SelectorEventLoop
from asyncio import Task, Future
from asyncio import Transport, DatagramTransport, Protocol, DatagramProtocol
from asyncio import StreamReader, StreamWriter, start_server, open_connection


# -------------------------- Transport + Protocol 使用 --------------------------------
class ProtocolEchoServer(Protocol):
    def connection_made(self, transport: Transport) -> None:
        peername = transport.get_extra_info('peername')
        print(f"Connection from {peername}")
        self.transport = transport

    def data_received(self, data: bytes) -> None:
        message = data.decode()
        print(f"Data Received: {message}")
        # 回显数据
        print(f'Send: {message}')
        self.transport.write(data)
        # 关闭传输
        print('Close the client socket')
        self.transport.close()

    def connection_lost(self, exc: Exception | None) -> None:
        if exc:
            print("Connection lost due to error")
        else:
            print("Connection closed")


class ProtocolEchoClient(Protocol):
    def __init__(self, message: str, on_con_lost: Future):
        self.message = message
        self.on_con_lost = on_con_lost

    def connection_made(self, transport: Transport):
        self.transport = transport
        print(f"Send: {self.message}")
        self.transport.write(self.message.encode())

    def data_received(self, data: bytes) -> None:
        print(f"Received: {data.decode()}")
        self.transport.close()  # 收到回复后关闭

    def connection_lost(self, exc: Exception | None) -> None:
        print("Connection closed")
        self.on_con_lost.set_result(True)


async def run_protocol_echo_server():
    loop: AbstractEventLoop = asyncio.get_running_loop()
    server: Server = await loop.create_server(
        lambda: ProtocolEchoServer(),
        '127.0.0.1', 8888
    )
    print("Server listening on 127.0.0.1:8888")
    async with server:
        await server.serve_forever()


async def run_protocol_echo_client():
    loop = asyncio.get_running_loop()
    on_con_lost: Future = loop.create_future()
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
    """
    open_connection 里注册的服务端回调函数，每次有新的客户端连接建立时，就会调用此函数，并传入一对 (StreamReader, StreamWriter).
    :param reader:
    :param writer:
    :return:
    """
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
    await writer.drain()  # 刷新缓冲区  --------- KEY

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
