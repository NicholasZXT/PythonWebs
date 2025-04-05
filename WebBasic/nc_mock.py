# coding: utf-8
"""
模拟 nc 命令向服务器发送消息，用于测试 Spark Streaming 和 Flink
"""
import sys
import os
import socket
import signal
from time import sleep
from datetime import datetime
from typing import Generator, Callable

def get_now_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def signal_handler(sig, frame):
    print(f"\n[{get_now_time()}] 收到 Ctrl+C，正在退出服务器...")
    sys.exit(0)


def run_nothing(sleep_seconds: int = 5):
    """测试是否能接收到 Ctrl+C 信号，退出程序"""
    signal.signal(signal.SIGINT, signal_handler)
    cnt = 1
    while True:
        print(f"[{get_now_time()}] running at loop [{cnt}] ...")
        sleep(sleep_seconds)
        cnt += 1


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
            print(f"[{get_now_time()}] Sending >>> : {message}")
            sock.sendall(message.encode('utf-8'))


def nc_server(host: str, port: int, messages: Callable[[], Generator[str, None, None]]):
    # 创建一个TCP/IP套接字
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 绑定套接字到地址和端口
    server_socket.bind((host, port))
    # 监听传入连接
    server_socket.listen(1)
    print(f"[{get_now_time()}] 服务器正在监听 {host}:{port}...")
    # 设置信号处理函数
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    try:
        while True:
            # 等待连接
            try:
                # 这里阻塞时，会导致主线程无法收到 Ctrl + C 信号 --------- KEY
                client_socket, client_address = server_socket.accept()
            except KeyboardInterrupt as e:
                break
            try:
                print(f"[{get_now_time()}] 连接来自: {client_address}, 准备发送数据")
                for message in messages():
                    print(f"[{get_now_time()}] Sending >>> : {message}", end='')
                    client_socket.sendall(message.encode('utf-8'))
                print(f"[{get_now_time()}] Sending message done.")
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
                print(f"[{get_now_time()}] 收到 Ctrl+C，正在退出客户端...")
                # client_socket.close()
                break
            finally:
                # 清理连接
                client_socket.close()
    except KeyboardInterrupt as e:
        print(f"[{get_now_time()}] 收到 Ctrl+C，正在退出服务器...")
    finally:
        server_socket.close()


def read_file(file_path: str, time_separator='>>>batch', interval_seconds=2, encoding='utf-8') -> Callable[[], Generator[str, None, None]]:
    def file_content_generator() -> Generator[str, None, None]:
        with open(file_path, 'r', encoding=encoding) as file:
            for line in file:
                if len(line) == 0 or line.startswith('\n'):
                    continue
                if line.startswith(time_separator):
                    print(f"[{get_now_time()}] >>>batch done, sleeping for {interval_seconds} seconds...")
                    sleep(interval_seconds)
                    continue
                yield line.strip(' ')
    # 返回的是生成器函数，不是生成器对象本身
    # return file_content_generator()
    return file_content_generator


if __name__ == "__main__":
    # 测试信号 Ctrl+C
    # run_nothing(5)

    cur_dir = os.getcwd()
    server_ip = '127.0.0.1'
    server_port = 9700
    print(f">>> current path: {cur_dir}.")
    file_path = os.path.join(os.getcwd(), "wordcount.txt")
    content_generator = read_file(file_path)
    # print("[{get_now_time()}] --------------")
    # for line in content_generator():  # 注意是函数调用的形式
    #     print(line, end='')
    # 注意多次调用
    # print("[{get_now_time()}] --------------")
    # for line in content_generator():
    #     print(line, end='')
    # print("[{get_now_time()}] --------------")
    # for line in content_generator():
    #     print(line, end='')

    # 作为服务端
    nc_server(server_ip, server_port, content_generator)

    # 作为客户端
    # nc_client(server_ip, server_port, content)

