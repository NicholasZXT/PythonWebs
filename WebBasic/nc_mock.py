# coding: utf-8
"""
模拟 nc 命令向服务器发送消息，用于测试 Spark Streaming 和 Flink
"""
from typing import Generator
import sys
import os
import socket
import signal
from time import sleep

def nc_client(server_ip, server_port, messages):
    # 创建一个TCP/IP套接字
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        # 连接到服务器
        sock.connect((server_ip, server_port))
        # 发送消息
        # sock.sendall(message.encode('utf-8'))
        # 接收响应（如果需要）
        # response = sock.recv(1024)
        # print(f"Received: {response.decode('utf-8')}")
        for message in messages:
            print(f"Sending >>> : {message}")
            sock.sendall(message.encode('utf-8'))


def signal_handler(sig, frame):
    print("\n收到 Ctrl+C，正在退出服务器...")
    sys.exit(0)

def nc_server(host: str, port: int, messages: Generator[str, None, None]):
    # 创建一个TCP/IP套接字
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 绑定套接字到地址和端口
    server_socket.bind((host, port))
    # 监听传入连接
    server_socket.listen(1)
    print(f"服务器正在监听 {host}:{port}...")
    # 设置信号处理函数
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    try:
        while True:
            # 等待连接
            try:
                client_socket, client_address = server_socket.accept()
            except KeyboardInterrupt as e:
                break
            try:
                print(f"连接来自: {client_address}, 准备发送数据")
                for message in messages:
                    print(f"Sending >>> : {message}", end='')
                    client_socket.sendall(message.encode('utf-8'))
                print(f"Sending message done.")
                # 接收数据
                # while True:
                #     data = client_socket.recv(1024)
                #     if data:
                #         print(f"收到数据: {data.decode('utf-8')}")
                #         # 发送数据回客户端
                #         client_socket.sendall(data)
                #     else:
                #         break
            except KeyboardInterrupt as e:
                print(f"收到 Ctrl+C，正在退出客户端...")
                # client_socket.close()
                break
            finally:
                # 清理连接
                client_socket.close()
    except KeyboardInterrupt as e:
        print(f"收到 Ctrl+C，正在退出服务器...")
    finally:
        server_socket.close()


def read_file(file_path: str, time_separator='>>>batch', interval_seconds=2, encoding='utf-8') -> Generator[str, None, None]:
    with open(file_path, 'r', encoding=encoding) as file:
        for line in file:
            if len(line) == 0 or line.startswith('\n'):
                continue
            if line.startswith(time_separator):
                print(f">>>batch done, sleeping for {interval_seconds} seconds...")
                sleep(interval_seconds)
                continue
            yield line.strip(' ')


if __name__ == "__main__":
    cur_dir = os.getcwd()
    server_ip = '127.0.0.1'
    server_port = 9700

    print(f">>> current path: {cur_dir}.")
    file_path = os.path.join(os.getcwd(), "wordcount.txt")
    content = read_file(file_path)
    # for line in content:
    #     print(line)

    # 作为服务端
    nc_server(server_ip, server_port, content)

    # 作为客户端
    # nc_client(server_ip, server_port, content)

