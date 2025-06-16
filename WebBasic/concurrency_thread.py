"""
Python并发编程-线程

Thread 相关的源文件只有 threading.py，它的底层是 _thread.py。

Python线程同步原语有如下几类：
- Lock
- RLock
- Condition
- Semaphore/BoundedSemaphore
- Event
- Barrier

Python里的多线程并发编程相比Java要简单很多，没有 synchronize, volatile 等关键字，主要原因（针对CPython实现）如下：
1. Python里面大部分的单次操作/方法都是原子性的，这里的原子性准确来说是该操作对应的是Python字节码的一行，再加上GIL的存在，所以不太需要 synchronize
2. Python里的读写操作，都是从主内存里读取的，同样也加上GIL的存在，所以多线程里不会出现CPU缓存不一致的情况，也就不需要 volatile 关键字
另外，CPython里的多线程，多线程 Python 程序不会从头到尾只使用一个 CPU 核心，但受 GIL 限制，同一时间只有一个线程是活跃的。
"""

import os
import random
from time import sleep, time
# import _thread
from threading import Thread, Condition, Lock, RLock, Event, Semaphore, BoundedSemaphore, Barrier, BrokenBarrierError
from threading import current_thread, currentThread, main_thread, get_ident, get_native_id, active_count, enumerate, local, stack_size
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError, CancelledError, ALL_COMPLETED, as_completed, wait
from queue import Queue  # 这个队列是线程安全的

def thread_basic_usage():
    """
    Thread 类代表在独立控制线程运行的活动。
    有两种方式指定活动：传递一个可调用对象给构造函数或者在子类重载 run() 方法。
    其它方法不应该在子类被（除了构造函数）重载。
    换句话说，只能 重载这个类的 __init__() 和 run() 方法。
    当线程对象一旦被创建，其活动必须通过调用线程的 start() 方法开始，这会在独立的控制线程中唤起 run() 方法。
    基本线程使用
    1. 方法一，传入线程里要执行的函数
    2. 方法二，继承线程类，并重载run方法
    """

    def thread_func(num, **kwargs):
        thread_id = get_ident()
        thread_name = current_thread().name
        print(f"[Thread-{thread_id}] starting ...")
        print(f"[Thread-{thread_id}:{thread_name}] run with num: {num}, kwargs: {kwargs}")
        sleep(0.2)
        print(f"[Thread-{thread_id}] ending.")

    class MyThread(Thread):
        def __init__(self, num, name):
            # 继承 Thread 类之后，初始化方法里，必须要首先调用 Thread.__init__() --------------- KEY
            if name:
                super().__init__(name=name)
            else:
                super().__init__()
            self.num = num

        # 重写 run 方法，注意，虽然重写了 run 方法，但是不要直接调用 run 方法，而是调用 start 方法
        def run(self):
            thread_id = get_ident()
            thread_name = current_thread().name
            print(f"[Thread-{thread_id}] starting ...")
            print(f"[Thread-{thread_id}:{thread_name}] run with num: {self.num}")
            sleep(0.2)
            print(f"[Thread-{thread_id}] ending.")

    # 创建线程
    # 方法一：
    t1 = Thread(
        target=thread_func,          # 指定线程中执行的 Callable 对象，这里是一个简单的function
        name="FunctionThread",       # 设置线程名称，默认是 Thread-%d
        args=("101",),               # 传递给 Callable 对象的位置参数
        kwargs={"some": "value"}     # 传递给 Callable 对象的关键字参数
    )
    # 方法二：
    t2 = MyThread(num="102", name="SubClassThread")

    print(f"main thread starts sub threads...")
    # 开始线程
    t1.start()
    t2.start()
    # 由于 GIL 的限制，如果主进程一直在执行，那么就不会释放 GIL ，导致该进程中的其他线程拿不到控制权  ----------- KEY
    # 所以如果下面一直在执行 while 循环，到不了 join，那么子进程就一直不会执行
    # while True:
    #     print('main thread running.')
    # join表示 主线程 在此处阻塞，等待线程执行结束后再继续，只有主线程阻塞了，其他线程才能拿到CPU
    print(f"main thread join...")
    t1.join()
    t2.join()
    print(f"main thread end.")


def thread_function_usage():
    """
    thread.py 模块提供了一些工具函数
    :return:
    """
    # 返回主 Thread 对象
    print(f"Main thread: {main_thread()}")
    # currentThread 是 current_thread() 的别名，被标记为 Deprecated
    print(f"Thread Current: {current_thread()}")
    print(f"Thread Name: {current_thread().name}")
    # 返回当前线程的 “线程标识符”。它是一个非零的整数。它的值没有直接含义，主要是用作 magic cookie，可能被后续线程复用
    print(f"Thread ID: {get_ident()}")
    print(f"Thread Native ID: {get_native_id()}")
    # 返回当前存活的 Thread 对象的数量
    print(f"Thread Count: {active_count()}")
    # 返回当前所有存活的 Thread 对象的列表
    print(f"Thread List: {enumerate()}")

    # Thread local 值
    mydata = local()
    mydata.x = 1


# ---------------- 带有锁 的线程同步 ---------------------
# 线程里迭代的次数
COUNT = 200
shared_resource_with_lock = 0
shared_resource_without_lock = 0

def thread_lock_usage():
    # 线程锁
    lock = Lock()

    # 没有锁管理 的两个线程函数
    def increment_without_lock():
        global shared_resource_without_lock
        for i in range(COUNT):
            # print("increment without lock: ", shared_resource_without_lock)
            # += 这个操作 在字节码层面 不是原子性的
            shared_resource_without_lock += 1
            sleep(0.05)

    def decrement_without_lock():
        global shared_resource_without_lock
        for i in range(COUNT):
            # print("decrement without lock: ", shared_resource_without_lock)
            shared_resource_without_lock -= 1
            sleep(0.05)

    # 带有锁管理的 两个线程函数
    def increment_with_lock():
        # 引入全局变量，这一句必须要有，它表示要 读并写 函数外部的变量
        global shared_resource_with_lock
        # COUNT 这个全局变量只是读，所以不需要 global 关键字
        for i in range(COUNT):
            # 手动获得锁，也可以像下面那样使用 with 语句
            lock.acquire()
            # print("increment with lock: ", shared_resource_with_lock)
            shared_resource_with_lock += 1
            # 手动释放锁
            lock.release()
            sleep(0.05)

    def decrement_with_lock():
        global shared_resource_with_lock
        for i in range(COUNT):
            # 使用 with 语句管理锁的获取和释放
            with lock:
                # print("decrement with lock: ", shared_resource_with_lock)
                shared_resource_with_lock -= 1
            sleep(0.05)

    # --------------- 线程锁的使用 -----------------------
    t1 = Thread(target=increment_without_lock)
    t2 = Thread(target=decrement_without_lock)
    t3 = Thread(target=increment_with_lock)
    t4 = Thread(target=decrement_with_lock)

    global shared_resource_without_lock
    global shared_resource_with_lock
    # 下面的这个无锁冲突演示，实践中不那么容易成功
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    print("----- shared_resource_with_no_lock: ", shared_resource_without_lock, "-----")
    t3.start()
    t4.start()
    t3.join()
    t4.join()
    print("----- shared_resource_with_lock: ", shared_resource_with_lock, "-----")


def thread_rlock_usage():
    """
    上面的 Lock 只能被一个线程获取一次，如果同一个线程尝试再次获取已经被它持有的锁，会导致**死锁**。
    而 RLock 相比 Lock，有如下特点：
    - 可以被**同一个线程**多次获取，多次获取时不会阻塞同一个线程
    - 内部维护了一个递归计数器，每获取一次加1，每次释放减1，直到计数为0才真正释放锁。
    - **重入锁必须由获取它的线程释放**，acquire 了多少次，也必须 release 多少次。
    - 更适合嵌套调用或递归函数中的加锁场景。
    - 性能相比 Lock 略低
    RLock 的 acquire() / release() 方法也支持 with 管理器。
    :return: None
    """
    # 这里使用一个递归函数来演示 RLock
    rlock = RLock()
    # lock = Lock()  # 改为使用 Lock 会阻塞自身

    def recursive_function(n):
        with rlock:
            print(f"---> enter recursive function, current level: {n}")
            if n > 0:
                recursive_function(n - 1)  # 递归调用
            print(f"<--- exit recursive function, current level: {n}")

    # 创建并启动线程
    t = Thread(target=recursive_function, args=(3,))
    t.start()
    t.join()


def thread_semaphore_usage():
    """
    信号量 Semaphore 是最古老的同步原语之一，用于同步**多个线程**对共享资源与数据的访问 。
    信号量对象内部管理着一个原子性的计数器，该计数器：
    - 计数器的值永远不会小于零
    - 因 `acquire()` 方法（P方法）的调用而递减，
    - 因 `release()` 方法（V方法）的调用而递增。
    - 当 `acquire()` 方法发现计数器为零时，将会阻塞，直到其它线程调用 `release()` 方法。

    此外Python还提供了一个 BoundedSemaphore 实现了有界信号量，以确保它当前的值不会超过初始值。

    相比于`Lock`/`RLock`，`Semaphore`允许多个（指定的值）线程同时访问。
    :return: None
    """
    # 使用信号量来实现 生产者-消费者模型
    # 缓冲区最大容量
    BUFFER_SIZE = 5
    BUFFER = []

    # 初始化 3 个信号量
    mutex = Lock()                    # 互斥锁 —— 可以使用 Lock 来代替
    empty = Semaphore(BUFFER_SIZE)    # 空位数量
    full = Semaphore(0)               # 已填充数据数量

    def producer():
        while True:
            empty.acquire()  # 等待有空位
            mutex.acquire()
            try:
                BUFFER.append(1)
                print(f"[Producer] produces 1 item, current buffer size: {len(BUFFER)}")
            finally:
                mutex.release()
            full.release()  # 增加一个已填满的位置
            sleep(0.5)      # 模拟生产时间

    def consumer():
        while True:
            full.acquire()  # 等待有数据
            mutex.acquire()
            try:
                BUFFER.pop()
                print(f"[Consumer] consumes 1 item, current buffer size: {len(BUFFER)}")
            finally:
                mutex.release()
            empty.release()  # 增加一个空位
            sleep(1)         # 模拟消费时间

    # 创建线程
    t_producer = Thread(target=producer, name='Producer', daemon=True)
    t_consumer = Thread(target=consumer, name='Consumer', daemon=True)

    # 启动线程
    t_producer.start()
    t_consumer.start()

    # 主线程保持运行（避免程序退出）
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        print("程序结束")


def thread_condition_usage():
    """
    条件变量 Condition 对象允许一个或多个线程在被其它线程所通知之前进行等待，**用于协调多个线程之间的执行顺序**：
    - 线程可以在某个条件不满足时进入等待状态（`wait()`）。
    - 当条件变化后，由另一个线程发出通知（`notify()` 或 `notify_all()`），唤醒等待的线程。
    - 通常配合一把锁（默认是 `RLock`）使用，确保对共享资源的访问是线程安全的。
    :return: None
    """
    # 使用信号量来实现 生产者-消费者模型
    # 缓冲区最大容量
    BUFFER_SIZE = 5
    BUFFER = []

    # 创建 Condition 对象（默认使用 RLock）
    condition = Condition()

    def producer():
        while True:
            with condition:
                while len(BUFFER) == BUFFER_SIZE:
                    print("[Producer] buffer is full, now waiting...")
                    condition.wait()  # 等待消费者消费
                BUFFER.append(1)
                print(f"[Producer] produces 1 item, current buffer size: {len(BUFFER)}")
                condition.notify()  # 通知消费者
            sleep(0.5)

    def consumer():
        while True:
            with condition:
                while not BUFFER:
                    print("[Consumer] buffer is empty, now waiting...")
                    condition.wait()  # 等待生产者生产
                BUFFER.pop()
                print(f"[Consumer] consumes 1 item, current buffer size: {len(BUFFER)}")
                condition.notify()  # 通知生产者
            sleep(1)

    # 创建线程
    t_producer = Thread(target=producer, daemon=True)
    t_consumer = Thread(target=consumer, daemon=True)

    # 启动线程
    t_producer.start()
    t_consumer.start()

    # 主线程保持运行
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        print("程序结束")


def thread_event_usage():
    """
    最简单的线程通信机制之一：一个线程发出事件信号，而其他线程等待该信号。
    一个 Event 对象管理一个内部标识：
    - 调用 `set()` 方法可将其设置为 true
    - 调用 `clear()` 方法可将其设置为 false，之后被`wait()`方法阻塞的线程会被唤醒。
    - 调用 `wait(timeout=None)` 方法将进入阻塞直到标识为 true 。

    Event 机制不太适合经典的 消费者-生产者 场景问题。

    :return: None
    """
    # 假设我们有多个子线程等待某个全局信号，只有当主线程发出信号后，所有子线程才开始执行任务
    event = Event()

    def worker(wid):
        print(f"Worker {wid} waiting for signal...")
        event.wait()  # 阻塞直到收到信号
        print(f"Worker {wid} received signal, running...")

    # 创建多个子线程
    threads = [Thread(target=worker, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()

    print("Main thread is preparing...")
    sleep(2)

    # 发送信号，让所有子线程继续执行
    event.set()

    # 等待所有子线程完成
    for t in threads:
        t.join()

    event.clear()


def thread_barrier_usage():
    """
    `Barrier`提供的同步原语主要用于应对固定数量的线程需要彼此相互等待的情况。
    简单来说就是“**让一组线程都到达某个点后才一起继续执行**”，常用于需要多个线程“集合”后再统一出发的场景。

    Barrier 机制也不太适合经典的 消费者-生产者 场景问题。

    :return: None
    """
    # 定义屏障，要求3个线程同时到达
    barrier = Barrier(3)

    def task(tid):
        print(f"Task {tid} start...")
        sleep(1)  # 模拟Task准备时间
        print(f"Task {tid} prepared, wait other tasks...")
        barrier.wait()  # 等待其他线程也到达屏障点
        print(f"Task {tid} continues running.")

    # 创建多个线程
    threads = [Thread(target=task, args=(i,)) for i in range(3)]

    # 启动所有线程
    for t in threads:
        t.start()

    # 等待所有线程完成
    for t in threads:
        t.join()


def thread_queue_usage():
    """
    多线程 + 线程队列 的生产者-消费者模型
    使用的是 queue.Queue 这个线程安全的队列，当然，多线程也可以使用 multiprocess.Queue
    :return:
    """
    class Producer(Thread):
        def __init__(self, name, queue: Queue):
            super().__init__()
            self.name = name
            self.queue = queue

        def run(self):
            thread_id = get_ident()
            pid = os.getpid()
            for i in range(10):
                item = random.randint(0, 256)
                # queue.Queue的put方法，block=True表示队列已满时会阻塞
                self.queue.put(item, block=True)
                print("thread '{}' in process '{}' is running".format(thread_id, pid))
                print('Producer notify: item {} is append to queue by {}'.format(item, self.name))
                sleep(0.5)

    class Consumer(Thread):
        def __init__(self, name, queue: Queue):
            super().__init__()
            self.name = name
            self.queue = queue

        def run(self):
            thread_id = get_ident()
            pid = os.getpid()
            while True:
                # queue.Queue的get方法，block=True表示队列为空时会阻塞
                item = self.queue.get(block=True, timeout=5)
                print("thread '{}' in process '{}' is running".format(thread_id, pid))
                print("Consumer notify: item {} is popped from queue by {}".format(item, self.name))
                # queue.Queue的task_done() 方法用于通知队列已处理一个任务
                # self.queue.task_done()

    # --------多线程+队列 的 生产者-消费者 模型 --------------
    # 这里的 queue.Queue 是线程安全的队列数据结构
    queue = Queue(3)
    t1 = Producer('Producer-1', queue)
    t2 = Consumer('Consumer-1', queue)
    t3 = Consumer('Consumer-2', queue)
    t1.start()
    t2.start()
    t3.start()
    t1.join()
    t2.join()
    t3.join()


def thread_pool_usage():
    """
    线程池使用
    :return: None
    """
    # 模拟一个耗时任务
    def task(n):
        # thread_info = f"[Thread-{get_ident()}:{current_thread().name}]"
        thread_info = f"[Thread-{get_ident()}]"
        print(f"{thread_info}start task with {n}")
        sleep(n)
        print(f"{thread_info}finished task with {n}.")
        return f"<{thread_info}Result: {n}>"

    # 创建一个最大线程数为3的线程池
    with ThreadPoolExecutor(max_workers=3) as executor:
        # 提交多个任务
        futures = [executor.submit(task, i) for i in [2, 1, 3, 2, 1]]
        # 按完成顺序获取结果
        for future in as_completed(futures):
            result = future.result()
            print("任务返回:", result)


def main():
    thread_basic_usage()
    thread_function_usage()
    thread_lock_usage()
    thread_rlock_usage()
    thread_semaphore_usage()
    thread_condition_usage()
    thread_event_usage()
    thread_barrier_usage()
    thread_queue_usage()
    thread_pool_usage()


if __name__ == '__main__':
    main()
