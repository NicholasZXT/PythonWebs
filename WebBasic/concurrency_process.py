"""
Python 并发编程 - 进程
"""
import os
import random
from time import sleep
# 多进程相关
from multiprocessing import Process, Pool
from multiprocessing import current_process, parent_process, cpu_count, active_children, get_start_method, \
    get_all_start_methods, get_context
from multiprocessing import Lock, RLock, Semaphore, BoundedSemaphore, Condition, Event, Barrier
from multiprocessing import Queue, SimpleQueue, JoinableQueue, Pipe, Value, Array
from multiprocessing.connection import Connection
from queue import Empty, Full    # 这个 queue 是线程同步队列，这里需要用到其中定义的 Empty 和 Full 异常
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from multiprocessing import Manager
from multiprocessing.managers import BaseManager, SyncManager, Namespace, SharedMemoryManager


def process_function_usage():
    """
    multiprocessing 提供了一系列工具函数
    :return:
    """
    # 获取当前进程
    print(f"Current Process: {current_process()}")
    print(f"Current Process Class: {type(current_process())}")   # <class 'multiprocessing.process._MainProcess'>
    print(f"Current Process Name: {current_process().name}")
    print(f"Current Process ID: {current_process().ident}")
    print(f"Current Process PID: {current_process().pid}")

    # 获取主进程，如果已经是主进程，则返回 None
    print(f"Parent Process: {parent_process()}")

    # 返回当前进程存活的子进程的列表
    print(f"Active Children: {active_children()}")

    # 返回CPU核数
    print(f"CPU Count: {cpu_count()}")
    # 当前进程可用的CPU核数要通过 os.sched_getaffinity(0) 获取 —— 这个API好像只有Linux有
    # print(f"Available CPU count: {len(os.sched_getaffinity(0))}")

    # 返回当前进程的启动方式
    print(f"Start method: {get_start_method()}")
    # 返回当前平台可用的启动方式
    print(f"All available start methods: {get_all_start_methods()}")

    # 获取当前进程上下文
    context = get_context()
    print(f"Context: {context}")


def process_basic_usage():
    """
    进程的 Process API 和 Thread 十分类似。
    方法一，传入进程里要执行的函数
    方法二、继承进程类，并重载run方法
    :return:
    """
    def subproc_func(num, **kwargs):
        process_info = f"[Process-{current_process().ident}:{current_process().name}]"
        print(f"[{process_info}] starting ...")
        print(f"[{process_info}] run with num: {num}")
        sleep(0.2)
        print(f"[{process_info}] ending.")

    class MyProcess(Process):
        def __init__(self, num, name):
            if name:
                super().__init__(name=name)
            else:
                super().__init__()
            self.num = num

        def run(self):
            process_info = f"[Process-{current_process().ident}:{current_process().name}]"
            print(f"[{process_info}] starting ...")
            print(f"[{process_info}] run with num: {self.num}")
            sleep(0.2)
            print(f"[{process_info}] ending.")

    # ------- 进程的基本使用 ------------------
    p1 = Process(target=subproc_func, name="process-1", args=("101",))
    p2 = MyProcess(name="process-1", num="103")
    p1.start()
    p2.start()
    p1.join()
    p2.join()


class Company:
    def __init__(self, person, company_name):
        # person 是一个 Person 类实例, company_name 是 str
        # 如果在这里打断点，debug停在这里时：
        # 1. 调用 id(person) 会发现和外面的 person 是同一个实例，表明实例对象可以将自己传入到另一个对象中
        # 2. 调用 person.print_company() 时会触发 AttributeError，提示 company_info 属性不存在——因为这里的 Company 对象还没完成实例化，
        # 所以外面 person 的 company_info 属性此时还没有创建，所以调用 print_company() 方法访问不到该属性
        self.person = person
        self.company_name = company_name

    def print_company(self):
        print(f"{self.person} is a member of company {self.company_name}.")


class Person:
    def __init__(self, name, company_name=None):
        self.name = name
        if company_name:
            # 注意，这里传入 self 表示 当前Person类实例对象本身
            self.company_info = Company(self, company_name)
        else:
            self.company_info = None

    def print_name(self):
        # 这个方法会被传递到子进程中执行，通过打印的如下信息，会发现在传递 print_name 方法的同时，也会将 当前类的实例传递到 子进程中
        # 但是 Linux 和  Windows 下不一样的是：
        # Linux是通过 fork() 产生子进程，子进程继承父进程里的所有对象，因此这里的 id(self) 等同于父进程的 id
        # Windows下是通过 pickle 之后传入子进程的，因此这里的 id(self) 不同于父进程里的 id
        print('Process : {}, PID: {}, object id(self): {}'.format(current_process(), os.getpid(), id(self)))
        print("Person name is :", self.name)

    def print_company(self):
        if self.company_info:
            self.company_info.print_company()
        else:
            print(f"{self.name} is freedom.")

    def __repr__(self):
        return "<Person.name: {}>".format(self.name)

def process_object_serialization():
    """
    对象在进程间的传递.
    创建进程时，使用继承Process的方法比较容易理解，但是使用传入函数涉及到对象时，会碰到如下两个问题：
    1. 某个对象可以将自身传入到另一个对象吗？             --- 可以
    2. 传入进程的函数是某个对象的方法时，会发生什么情况？   --- 会将当前对象也传入到子进程中，所以当前对象必须要是可序列化的
    :return:
    """
    # 初始化这个类的时候，检查一下 Company 类的实例过程
    p = Person('Daniel', 'Empire')
    # 开启子进程时，检查一下传入的内容
    print('Process : {}, PID: {}, object id(p): {}'.format(current_process(), os.getpid(), id(p)))
    proc = Process(target=p.print_name)
    proc.start()
    proc.join()


def process_queue_usage():
    """
    多进程 + 进程队列 的生产者-消费者模型
    :return:
    """
    def producer(name, queue):
        print("producer " + name + " is running")
        pid = os.getpid()
        i = 0
        while i < 20:
            item = random.randint(0, 50)
            queue.put(item)
            print("process '{}' is running".format(pid))
            print("producer {} putting item {} successfully".format(name, item))
            i = i+1
            sleep(0.5)

    def consumer(name, queue):
        pid = os.getpid()
        while True:
            # print("consumer {} get Queue size : {}".format(name, queue.qsize()))
            # item = queue.get()
            item = queue.get(block=True, timeout=5)
            print("process '{}' is running".format(pid))
            print("consumer {} getting item {} successfully.".format(name, item))
            sleep(0.5)

    # --------多进程+队列 的 生产者-消费者 模型--------------
    queue = Queue()
    p = Process(target=producer, args=('Producer-1', queue))
    c1 = Process(target=consumer, args=('Consumer-1', queue))
    c2 = Process(target=consumer, args=('Consumer-2', queue))
    p.start()
    c1.start()
    c2.start()
    p.join()
    c1.join()
    c2.join()

def process_pipe_usage():
    """
    多进程管道 Pipe 使用
    :return:
    """
    def worker(conn: Connection):
        print("子进程等待消息...")
        msg = conn.recv()  # 接收主进程发来的消息
        print(f"子进程收到: {msg}")
        conn.send("Hello from child")  # 回复
        conn.close()

    parent_conn, child_conn = Pipe()
    p = Process(target=worker, args=(child_conn,))
    p.start()
    parent_conn.send("Hello from parent")
    response = parent_conn.recv()
    print("主进程收到回复: ", response)
    p.join()


def process_synchronization_usage():
    """
    进程同步原语。
    multiprocess 模块提供了和 thread 模块一样的同步原语，包括：Lock, RLock, Semaphore, BoundedSemaphore, Condition, Event, Barrier.
    但是需要注意的是，同步原语在多进程环境中并不像它们在多线程环境中那么必要。
    多进程编程中，不推荐使用这些同步原语，一般使用消息机制（Queue, Pipe）实现进程间通信
    :return:
    """
    ...


def process_shared_memory_usage():
    """
    多进程共享状态。
    multiprocess 提供了如下 两个方式 实现跨进程共享状态：
    1. 共享内存：Value 和 Array
    2. Server Process: Manager 代理
    :return:
    """


# ======================== Manager 使用 =======================================
def process_manager_usage():
    """
    多进程 Server process 使用, 主要是使用 Manager 作为代理。
    :return:
    """
    from concurrency_process_ipc import worker_fun
    # 自定义Manager管理器，用作客户端
    class MyManagerClient(BaseManager):
        # 类的定义体中什么都不需要写
        pass

    # 这里注册共享对象时，只需要提供共享数据类型的 typeid ——它们对应于远程Manager服务端的共享数据类型
    # 由远程Manager服务端返回，所以这里不需要提供定义
    MyManagerClient.register('Maths')
    MyManagerClient.register('NumDict')

    manager_client = MyManagerClient(address=('localhost', 50000), authkey=b'abc')
    # 调用这一句连接远程Manager服务
    manager_client.connect()
    maths = manager_client.Maths(0, 0)
    num_dict = manager_client.NumDict()
    print(f'math.class: {maths.__class__}, math: {maths}')
    print(f'num_dict.class: {num_dict.__class__}, num_dict: {num_dict}')
    # 在下面的两个子进程中使用上述两个自定义共享对象的代理
    proc_list = [Process(target=worker_fun, args=(maths, num_dict, i)) for i in [1, 2]]
    for p in proc_list:
        p.start()
    for p in proc_list:
        p.join()
    print(f'math: {maths}')
    print(f'num_dict: {num_dict}')
    num_dict['a'] = 1
    # num_dict.setdefault('a', 1)
    print(f'num_dict: {num_dict}')


def process_pool_usage():
    """
    进程池使用
    :return:
    """
    def worker(level, msg):
        print("{} of {} starting, process id is: {}.".format(level, msg, os.getpid()))
        # random.random()随机生成0~1之间的浮点数
        sleep_time = random.random() * 5
        print("{} of {} sleep for {:.4f} second.".format(level, msg, sleep_time))
        sleep(sleep_time)
        return sleep_time

    def show(msg):
        print("msg '{}' starting, process id is: {}.".format(msg, os.getpid()))
        # random.random()随机生成0~1之间的浮点数
        sleep_time = random.random() * 5
        sleep(sleep_time)
        # print("msg '{}' sleep for {:.4f} second.".format(msg, sleep_time))
        # return sleep_time
        return msg

    # -------- Pool 的使用------------------
    # 使用 apply 方法，一次提交一个进程，并阻塞直到子进程执行完
    # 这种方式不必使用 join 等待，返回的结果就是直接是函数的返回结果
    with Pool(3) as pool:
        res = pool.apply(worker, ('process', 'worker-1'))
        # 返回值就是 worker方法 的返回值
        print("worker-1 is done, res is :", res)
        res = pool.apply(worker, ('process', 'worker-2'))
        print("worker-2 is done, res is :", res)
        res = pool.apply(worker, ('process', 'worker-3'))
        print("worker-3 is done, res is :", res)

    # 使用 apply_async 进行异步调用，返回的 res 是一个 pool.ApplyResult 对象
    # 必须要 使用 join 方法开启任务
    pool = Pool(3)
    res1 = pool.apply_async(worker, ('process', 'worker-1'))
    print("worker-1 is done, res is: ", res1)
    res2 = pool.apply_async(worker, ('process', 'worker-2'))
    print("worker-2 is done, res is: ", res2)
    res3 = pool.apply_async(worker, ('process', 'worker-3'))
    print("worker-3 is done, res is: ", res3)
    print(f"res1.__class__: {type(res1)}")
    # 判断是否执行完成，它不会抛出异常
    print(f"res1.ready(): {res1.ready()}")
    # 但是下面的这个方法会抛出 ValueError 异常
    # print(f"res1.successful(): {res1.successful()}")
    print("----start----")
    pool.close()  # 关闭进程池，关闭后po不再接收新的请求 —— 必须要在 .join() 前调用此方法
    pool.join()   # 等待po中所有子进程执行完成，再执行下面的代码,可以设置超时时间join(timeout=)
    print("-----end-----")
    # 在执行完成后检查则不会抛出异常
    print(f"res1.successful(): {res1.successful()}")
    # wait() 会等待结果执行完成，可以设置 timeout 参数，它不会返回任何值
    print(f"res1.wait(): {res1.wait()}")
    # get() 用于获取结果，可以设置 timeout 参数
    print(f"res1.get(): {res1.get()}")

    # 使用 map/starmap 方法一次提交多个进程，使用进程池中的所有进程并行执行某个函数 ----- 不太好用
    # map 只能给函数传一个参数，starmap 可以传入多个参数
    pool = Pool(3)
    # 这里由于 worker 有两个参数，所以要使用 starmap
    # res = pool.starmap(worker, [('process', 'worker-1')])
    res = pool.starmap(worker, [('process', 'worker-1'), ('process', 'worker-2'), ('process', 'worker-3')])
    # 上面的方法会阻塞，直到进程池执行完毕
    # 返回的 res 是一个 list，其中的值就是 worker 的返回值
    print(res)
    print("----start----")
    pool.close()  # 关闭进程池，关闭后po不再接收新的请求
    pool.join()  # 等待po中所有子进程执行完成，再执行下面的代码,可以设置超时时间join(timeout=)
    print("-----end-----")

    # Pool.map 方法有一个 chunksize 参数，指定一次传一批数据到子进程了，而不是每次传一条
    pool = Pool(2)
    # res = pool.map(show, [1, 2, 3, 4, 5, 6, 7, 8])
    res = pool.map(show, [1, 2, 3, 4, 5, 6, 7, 8], chunksize=4)
    # 返回的结果顺序并不会乱
    print(res)

    #  进程池
    future_list = []
    with ProcessPoolExecutor(max_workers=3) as executor:
        for i in range(3):
            future = executor.submit(worker, "Process",  i+1)
            future_list.append(future)
    for future in future_list:
        print("future.result: ", future.result())


def process_concurrent_pool_usage():
    ...


def process_singleton():
    """
    单例模式 + 多进程
    :return:
    """

    # 下面这个例子可以看出，单例模式的作用范围是 单进程，跨进程的话是可以有两个对象的，并且这两个对象的修改都是独立的
    class Single:
        __instance = None

        # 这里不是严格的单例模式，因为这个构造方法没有被隐藏起来
        def __init__(self, data):
            self.data = data

        @classmethod
        def get_instance(cls, data):
            if cls.__instance is None:
                # print('creating instance')
                cls.__instance = Single(data)
            return cls.__instance

        def print_data(self):
            print(self.data)

    def sub_proc(single: Single):
        single.data = 'new + ' + single.data
        print(f"id(single): {id(single)}")
        single.print_data()
        single_2 = Single.get_instance('new-data-2')
        print(f"id(single_2): {id(single_2)}")
        single_2.print_data()

    data = 'singleton'
    single = Single.get_instance(data)
    print(f"id(single): {id(single)}")
    single_2 = Single.get_instance(data)
    print(f"id(single_2): {id(single_2)}")
    single.print_data()
    proc = Process(target=sub_proc, args=(single,))
    proc.start()
    proc.join()
    single.print_data()


def main():
    process_function_usage()
    process_basic_usage()
    process_object_serialization()
    process_queue_usage()
    process_pipe_usage()
    process_shared_memory_usage()
    process_manager_usage()
    process_pool_usage()
    process_singleton()


if __name__ == '__main__':
    main()
