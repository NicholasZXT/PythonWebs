# coding: utf-8
"""
模拟 nc 命令向服务器发送消息，用于测试 Spark Streaming 和 Flink
"""
from typing import Generator
import os
import socket
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


def nc_server(host: str, port: int, messages: Generator[str, None, None]):
    # 创建一个TCP/IP套接字
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 绑定套接字到地址和端口
    server_socket.bind((host, port))
    # 监听传入连接
    server_socket.listen(1)
    print(f"服务器正在监听 {host}:{port}...")
    while True:
        # 等待连接
        client_socket, client_address = server_socket.accept()
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
        finally:
            # 清理连接
            client_socket.close()


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
    nc_client(server_ip, server_port, content)

