# coding: utf-8
"""
模拟 nc 命令向服务器发送消息，用于测试 Spark Streaming 和 Flink
"""
from typing import Generator
import os
import socket

def send_message_to_server(server_ip, server_port, messages):
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


def read_file(file_path: str) -> Generator[str, None, None]:
    with open(file_path, 'r') as file:
        for line in file:
            yield line


if __name__ == "__main__":
    # server_ip = '127.0.0.1'
    server_ip = '10.8.6.185'
    server_port = 9700
    # message = 'Hello, Server!'
    # send_message_to_server(server_ip, server_port, message)

    print(f">>> current path: {os.getcwd()}.")
    file_path = os.path.join(os.getcwd(), "wordcount.txt")
    content = read_file(file_path)
    # for line in content:
    #     print(line)

    send_message_to_server(server_ip, server_port, content)

