"""
自定义实现异步编程里的简化版 Future, Task, EventLoop。
基于《Python Concurrency with asyncio》 Chapter 14，略有改进。

实现完这个自定义EventLoop，可以发现异步编程中有一个重要的点：
await 本身并不“异步”，真正实现并发的是 Task 和事件循环的调度能力。

如果一个异步函数的内部调用及其嵌套调用，都是单纯的 await，那么该异步函数及其内部的异步调用，都只是串行的。
只有创建了 Task 并将其加入到事件循环中（当然后面还需要显式await该Task），才能实现真正的异步并发。

async/await 是异步的“语法基础”，但 Task + EventLoop 才是并发的“执行引擎”。

-------------------------------------------------------------------
关于 Reactor模型

- python异步编程中，asyncio默认提供的是 “单Reactor-单线程” 模型，
- 可以通过 `EventLoop.run_in_executor()` 方法支持 “单Reactor-多线程” 模型，
- 但是对于 “多Reactor-多线程” 模型（比如Java Netty框架提供），asyncio库本身不支持，除非使用其他的高级技巧（比如多进程）或第三方库。
"""
from typing import List, Dict, Union, Tuple, Any
from functools import partial
import socket
from socket import socket as socket_class
import selectors
from selectors import BaseSelector, DefaultSelector
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future as ConcurrentFuture
from datetime import datetime


SERVER_ADDRESS = ('127.0.0.1', 8080)

def get_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _Part_1():
    ...
# ================================ Part-1: 自定义 Future 对象 ================================
class CustomFuture:
    """
    自定义 Future 对象。
    Future 类可以表述为 “异步结果的占位符”，它是一个底层的 awaitable 对象，代表一个尚未完成的异步操作的结果（不是异步操作本身）。
    Future 有 3 种 API:
      - 实现 await 协议，这是异步的基础
      - 检查result/finish状态、设置result、获取result。 其中设置result的操作一般由异步框架执行，此方法和 异步机制（比如事件循环） 配合的关键点。
      - 添加回调函数。可选，一般回调函数都在 设置result 的方法里被调用。
    """

    def __init__(self):
        self._result = None
        self._is_finished = False
        self._done_callback = None
        self._exception = None

    def add_done_callback(self, fn):
        self._done_callback = fn

    def is_finished(self):
        return self._is_finished

    def result(self):
        if self._exception:
            raise self._exception
        return self._result

    def set_result(self, result):
        """
        设置 Future 对象的结果，并调用回调函数。
        """
        self._result = result
        self._is_finished = True
        if self._done_callback:
            self._done_callback(result)
            # 实际中回调函数的第一个参数，通常设置为 future 对象本身
            # self._done_callback(self, result)

    def set_exception(self, exc):
        self._exception = exc
        self._is_finished = True
        if self._done_callback:
            self._done_callback(self)

    def __await__(self):
        """
        __await__ 方法唯一的要求就是返回一个迭代器。在协程中，一般会返回一个生成器——它也是迭代器。
        使用 await future 语法时，内部原理大致为：
          1. 检查 future 对象是否实现了 __await__() 方法，没有则抛出 TypeError，有则调用 __await__() 获取返回的迭代器（生成器）
          2. 借助事件循环驱动迭代器（生成器），反复调用 .__next__()/.__anext__() 方法
          3. 直到迭代器抛出 StopIteration 异常，获取异常对象的 value，作为 await 表达式的值
        注意，Future 的 __await__() 方法返回的迭代器（生成器）里的元素，只有两种：
          1. Future 对象本身 —— await 内部遍历时获取的对象，此时会一直 “循环遍历”
          2. Future 对象完成时应当返回的内容 —— 它是 set_future() 放入的对象，也是 await future 时拿到的对象
        """
        # Future 对象的 __await__ 中，首先会检查是否已完成
        if not self._is_finished:
            # 如果没有完成，则 yield 返回自身 ---------------- KEY
            # 外部对象在遍历 __await__() 方法返回的迭代器时（比如使用 for 循环），
            # 只要Future 对象没有完成，那么外部遍历时拿到的始终是 future 对象自身。
            yield self
        # 只有 future 对象已完成，才会返回结果：返回的就是 set_result() 放入的对象
        return self.result()


def run_custom_future():
    """
    演示自定义 Future 对象的使用。
    """
    future = CustomFuture()
    i = 0
    while True:
        i += 1
        try:
            print(f'[{i}], Checking future...')
            # 这里不能使用 await future，因为 await 会阻塞直到获取 future 对象的 __await__() 方法返回值
            gen = future.__await__()
            next(gen)
            # gen.send(None)
            print(f'[{i}], Future is not done...')
            if i >= 3:
                # future对象的 set_result() 方法实际中会由事件循环调用，这里只是模拟一下
                print(f'[{i}], Setting future result...')
                # 下面的 StopIteration 的 value，就是 future.set_result() 放入的对象
                future.set_result(f"Finished@[{i}]")
        except StopIteration as e:
            print(f'[{i}], Future value is: {e.value}')
            break


def _Part_2():
    ...
# ================================ Part-2: 带 Future 对象的 socket + selector ================================
def run_socket_server_with_future():
    """
    使用 CustomFuture + async + await，构建了一个简单的异步服务器，其中包含了一个简单的事件循环实现。
    """
    def connect_callback(future: CustomFuture, connection: socket_class):
        """
        selector 上注册的回调函数，用于selector通知机制返回事件时，将接收到的 客户端socket 连接对象设置为 Future 的result.
        它的参数是自己定义的，不是 selectors 定义的。
        """
        print(f"[{get_now()}] Calling connect_callback with -> future: {future}, connection: {connection}")
        # 这里 set_result 的对象，就是 await future 获取到的对象
        future.set_result(connection)

    async def socket_accept(selector: BaseSelector, sock: socket_class):
        print(f"[{get_now()}] Registering socket and future to selector...")
        # 创建一个 future 对象，作为 客户端socket 的 异步占位符，不过这里并没有添加回调函数
        future = CustomFuture()
        # 向 selector 中注册 socket 和监听的事件类型后
        # 这里附加的 data 被设置为一个回调函数（使用partial封装了future后的偏函数），用于设置 future 的结果
        selector.register(fileobj=sock, events=selectors.EVENT_READ, data=partial(connect_callback, future))
        print(f"[{get_now()}] Waiting for socket client connection from future: {future}...")
        # Future对象作为 socket 对象的异步占位符，await 后的返回值就是 客户端socket 对象，它是在 connect_callback 中设置的
        connection: socket_class = await future
        return connection

    async def socket_server(selector: BaseSelector):
        # 创建 + 配置 socket
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(SERVER_ADDRESS)
        sock.listen()
        sock.setblocking(False)

        print(f"[{get_now()}] Starting socket server...")
        # 使用 selectors 通知系统监听客户端发起的 socket 连接，并结合 Future 对象，实现异步
        connection: socket_class = await socket_accept(selector, sock)
        print(f"[{get_now()}] Server received client connection: {connection}")
        # 出于简化目的，这里没有使用 while 循环，所以只会监听一次客户端的 socket 连接
        # 并且拿到 1个 客户端的socket之后，啥也没干，直接结束了
        # 并且这里也没有 接收客户端socket 发来的数据的操作
        # 上面这些被简化的操作会在事件循环里补齐

    # ------- socket + selector + CustomFuture 实现的异步服务器 --------------------
    selector = DefaultSelector()
    sock_coro = socket_server(selector)
    round_num = 0
    # 下面的 while 循环，其实就是一个简单的事件循环 -------------------- KEY
    while True:
        round_num += 1
        try:
            print(f"[{get_now()}][{round_num}] Send and Execute one step for socket server coroutine...")
            # 此处 send() 方法会激活 socket_server() 返回的协程对象，激活后：
            #   1. socket_server() 协程会执行到 await socket_listening() 处，然后在这里等待 socket_listening() 协程执行；
            #   2. socket_listening() 协程会执行到 await future 处，然后停在这里等待 future 返回结果
            #   3. 交出控制权，后面的代码继续执行
            send_result = sock_coro.send(None)

            # send() 方法返回值是一个 CustomFuture 对象，是由 socket_server -> await socket_accept() -> await future 这里返回的。
            # 对比输出日志中 Future 对象的地址可以确认这一点。
            print(f"[{get_now()}][{round_num}] Received send_result: {send_result}...")
            # 虽然这里没有用到 send_result，但是在多轮事件循环中，send_result 可以用于逐步保存 await 内部的返回结果

            # 执行这一句之前，上面的 sock_coro 协程会暂停在 socket_listening() 协程的 await future 处，将控制权交还给主线程
            print(f"[{get_now()}][{round_num}] selector polling...")
            # 这里会阻塞，直到 selectors 检查到socket客户端建立连接通知的 events ----------- KEY
            events = selector.select()
            for key, mask in events:
                print(f"[{get_now()}][{round_num}] selector receiving event -> key: {key}; mask: {mask}")
                callback = key.data
                print(f"[{get_now()}][{round_num}] selector event.key.data -> callback to use: {callback}")
                # callback 就是 connect_callback() 方法，这里手动调用 —— 也是这里决定了 connect_callback() 方法的参数 ------- KEY
                # 它会设置 future 的结果，并在 while 循环下一轮的 sock_coro.send(None) 处触发 socket_listening() 的返回
                callback(key.fileobj)
            print(f"[{get_now()}][{round_num}] selector polling done.")
        except StopIteration as e:
            # 这个 StopIteration 异常，是在 while 循环第 2 轮的 sock_coro.send(None) 处抛出的，因为 sock_coro 协程已经完成
            print(f"[{get_now()}][{round_num}] Socket server stopped.")
            break


def _Part_3():
    ...
# ================================ Part-3: Task 封装协程 ================================
class CustomTask(CustomFuture):
    """
    基于 CustomFuture 实现 CustomTask。
    Task类 是 协程的执行容器，用来包装一个协程（coroutine）并对其进行调度和管理。
    它的作用分为两个方面：
      - 继承自 Future 类，因此它也具有 异步结果占位符 的作用
      - 以组合的方式封装了一个协程，并提供了对该协程的生命周期的管理：驱动协程、取消协程、异常处理等
    由于继承了 Future 类，所以 Future 的部分不需要额外实现，需要实现的是对协程生命周期的管理相关API。
    此处的 Task 实现比较简单；
      - 重点放在 驱动协程 的实现
      - 未提供取消协程执行的API
      - 未提供异常处理
    """
    def __init__(self, coro, *args, **kwargs):
        super().__init__()
        # 以实例变量的方式封装协程 —— 组合
        self._coro = coro
        # 用于保存协程的 send() 方法返回的 Future 对象
        self._task_state: CustomFuture | CustomTask | None = None
        self._current_result = None
        # 作者本来的实现里还持有一个事件循环对象，但只是简单的向事件循环注册当前 Task，和Task其他部分没啥关系，
        # 反倒是在 Task 中调用 loop.register_task(self) 的方式使用起来很迷惑，所以这里注释掉了，
        # 而是改为让 EventLoop 在外面显式调用此方法，更符合 asyncio 的做法。
        # self._loop = loop
        # loop.register_task(self)

    def step(self):
        """
        触发当前 Task 所封装的 coro 的调用。
        此方法的重点在于：需要保证 执行完 coro协程 以及 它内部嵌套的协程。 --------- KEY
        此方法没有涉及 当前Task 的result设置，这个操作一般是由事件循环来完成的。
        """
        try:
            # 预激活协程，也就是首次运行协程，并将协程 send() 方法的返回值保存在 _task_state 中
            if self._task_state is None:
                self._task_state = self._coro.send(None)
            # -----------------------------------------------------------------------------------------------
            # 这里的原理是：
            # 当前Task对象持有的 _coro 内部可能会 await another_task/another_future，
            # 并且这些 awaitable 对象内部还可能继续嵌套调用 awaitable 对象，
            # 此时上面 _coro.send() 方法返回的 Task/Future 对象在每次调用 step() 方法时都是不一样的，
            # 每次调用 send() 方法，都会依次返回 嵌套await 后的 Task/Future 对象。
            # 那么如何触发 嵌套await 后的 Task/Future 对象的运行，直到获取当前 Task 封装的协程的运行结果？
            # 答案是对 send() 方法返回的 Future 设置一个 callback, 在 callback 里继续调用 step() 方法，实现 异步递归 的效果。
            # -----------------------------------------------------------------------------------------------
            # 对于协程send()方法返回的 Future/Task对象，设置一个回调，在回调里继续调用 step() 方法
            if isinstance(self._task_state, CustomFuture):
                self._task_state.add_done_callback(self._future_done)
        except StopIteration as e:
            self.set_result(e.value)

    def _future_done(self, result):
        """
        此回调函数用于实现 异步递归 调用 step() 的效果。
        这里有个问题是：异步递归的栈可能会很深，导致栈溢出，asyncio 使用了复杂的调度机制（ready队列，call_soon调用）来避免这个问题。
        """
        self._current_result = result
        try:
            self._task_state = self._coro.send(self._current_result)
        except StopIteration as e:
            self.set_result(e.value)


def _Part_4():
    ...
# ================================ Part-4: 自定义事件循环 ================================
class CustomEventLoop:
    """
    自定义事件循环。
    事件循环里最重要的是如下 3个功能：
    1. 需要提供一个方法接受主入口协程，类似于 asyncio.run()
    2. 需要提供一个方法来注册一个 CustomTask
    3. 需要一组方法来处理 socket 相关的操作：接收连接，接收数据，关闭socket。这组方法将基于 selectors 实现。
    """

    def __init__(self):
        self.selector = DefaultSelector()
        # asyncio 里使用了 collections.deque 来保存 task
        self._tasks_to_run: List[CustomTask] = []
        self.current_result = None
        # 下面这个是模拟 asyncio 里 event_loop 的 run_in_executor() 方法，
        self._default_executor: ThreadPoolExecutor | ProcessPoolExecutor = ThreadPoolExecutor(max_workers=4)  # 默认线程池
        self._lock = threading.Lock()

    # --------------------- 注册Task ----------------------
    def register_task(self, task):
        self._tasks_to_run.append(task)

    # --------------------- 主协程入口 ----------------------
    def run(self, coro):
        round_num = 0
        # 入口主协程使用 send() 方法激活
        print(f"[{get_now()}][{self.__class__.__name__}] Start run entry coroutine...")
        self.current_result = coro.send(None)
        while True:
            round_num += 1
            # ------- 主协程没有使用 Task 封装，而是使用 send() 驱动执行 ---------
            # 其实也可以将主协程封装为 Task，这样协程的驱动逻辑就更加统一。
            print(f"[{get_now()}][{self.__class__.__name__}][{round_num}] Execute one step for entry coroutine...")
            try:
                if isinstance(self.current_result, CustomFuture):
                    self.current_result.add_done_callback(self._set_current_result)
                    if self.current_result.result() is not None:
                        self.current_result = coro.send(self.current_result.result())
                else:
                    self.current_result = coro.send(self.current_result)
            # 主协程抛出 StopIteration 异常，则表示主协程及其内部嵌套的协程执行完毕，可以获取结果了。
            except StopIteration as e:
                print(f"[{get_now()}][{self.__class__.__name__}][{round_num}] Entry coroutine completed.")
                # 主协程执行完，直接返回
                return e.value
                # 此处返回后，self._tasks_to_run 中未完成的 Task 不再有机会运行，因为这些 Task 肯定没有在主协程及其嵌套协程中被 await，
                # 这也是 asyncio.run() 的行为。

            # ----- 事件循环中注册的其他协程都被封装为 Task 对象，在这里使用 step() 方法驱动执行 ---------
            # self._tasks_to_run 中的Task，是在主协程中使用 loop.register() 方法注册的，
            # 要特别注意的是，这些 task 一定要使用 await，否则可能执行不完，原因见上面
            print(f"[{get_now()}][{self.__class__.__name__}][{round_num}] run tasks in loop...")
            for task in self._tasks_to_run:
                task.step()
            # 收集未完成的 Task，下一轮 while 循环中继续执行
            self._tasks_to_run = [task for task in self._tasks_to_run if not task.is_finished()]

            # ----- 阻塞等待/处理 selector 中事件 ---------
            print(f"[{get_now()}][{self.__class__.__name__}][{round_num}] Selector polling events...")
            events = self.selector.select()
            print(f"[{get_now()}][{self.__class__.__name__}][{round_num}] Processing selector events...")
            for key, mask in events:
                callback = key.data
                callback(key.fileobj)
            print(f"[{get_now()}][{self.__class__.__name__}][{round_num}] {'-----'*20}")

    def _set_current_result(self, result):
        self.current_result = result

    # --------------------- socket 操作 ----------------------
    def _register_socket_to_read(self, sock: socket_class, callback) -> CustomFuture:
        """
        此方法主要用于处理 selector 中 客户端socket 的两种情况：
          1. 客户端socket 连接建立事件，在 selector 中注册 accept_connection() 处理
          2. 客户端socket 发送了数据， 在 selector 中注册 received_data() 处理
        """
        # future 对象是作为 客户端socket 的异步连接占位符
        future = CustomFuture()
        try:
            # 如果 socket 已经被注册过了，则表示是 socket客户端发送数据的情况
            self.selector.get_key(sock)
        except KeyError:
            # 如果 socket 没有被注册过，则表示是 socket客户端连接建立 的情况
            # 注意，客户端socket 也要设置为非阻塞模式
            sock.setblocking(False)
            self.selector.register(sock, selectors.EVENT_READ, partial(callback, future))
        else:
            self.selector.modify(sock, selectors.EVENT_READ, partial(callback, future))
        return future

    async def sock_accept(self, sock: socket_class) -> Tuple[socket_class, Any]:
        """
        此方法的返回值就是 accept_connection 中 sock.accept() 的返回值
        """
        print(f"[{get_now()}] Registering socket to listen for client connection...")
        return await self._register_socket_to_read(sock, self.accept_connection)

    def accept_connection(self, future: CustomFuture, sock: socket_class) -> None:
        print(f"[{get_now()}] Accepting connection from client socket: {sock}...")
        # socket.accept() 方法返回的是一个元组：(socket object, address info)
        result: Tuple[socket_class, Any] = sock.accept()
        future.set_result(result)

    async def sock_recv(self, sock: socket_class) -> bytes:
        """
        此方法的返回值就是 received_data 中 socket.recv() 的返回值
        """
        print(f"[{get_now()}] Registering socket to listen for data...")
        return await self._register_socket_to_read(sock, self.received_data)

    def received_data(self, future: CustomFuture, sock: socket_class) -> None:
        print(f"[{get_now()}] Received data from client socket: {sock}...")
        data = sock.recv(1024)
        future.set_result(data)

    def sock_close(self, sock: socket_class):
        self.selector.unregister(sock)
        sock.close()

    # --------------------- run_in_executor() 方法实现 ----------------------
    def set_default_executor(self, executor):
        """设置默认执行器"""
        self._default_executor = executor

    def run_in_executor(self, executor: Union[None, ThreadPoolExecutor, ProcessPoolExecutor], func, *args):
        """
        异步执行一个阻塞函数。
        :param executor: 执行器（ThreadPoolExecutor / ProcessPoolExecutor），None 表示使用默认线程池
        :param func: 要执行的函数
        :param args: 函数参数
        :return: CustomFuture 对象，可 await
        """
        # 如果未指定执行器，使用默认线程池
        if executor is None:
            executor = self._default_executor

        # 创建一个 Future，作为 ThreadPoolExecutor/ProcessPoolExecutor submit方法 运行结果的异步占位符
        future = CustomFuture()

        def _executor_callback(future_from_executor: ConcurrentFuture):
            """
            这是提交给线程/进程池 Future 的回调函数，当后台任务完成时，此函数被调用。
            注意，这里的 future 对象是 concurrent.futures.Future.
            """
            try:
                # 获取执行结果
                result = future_from_executor.result()
                # 设置 asyncio Future 的结果，触发 await 恢复
                # 这里的 future 是 CustomFuture，直接使用外部函数的 future 对象
                future.set_result(result)
            except Exception as ex:
                # 如果后台任务抛出异常，也设置到 Future，需要在 CustomFuture 中添加 set_exception 方法
                future.set_exception(ex)

        # 将函数提交到执行器
        # submit() 立即返回一个 concurrent.futures.Future
        try:
            future_from_executor: ConcurrentFuture = executor.submit(func, *args)
        except Exception as e:
            # 如果 submit 失败，直接设置异常
            future.set_exception(e)
            return future

        # 为执行器的 Future 添加完成回调
        # 当线程/进程中的任务完成时，_callback 会被调用
        future_from_executor.add_done_callback(
            lambda fut: self.call_soon_threadsafe(_executor_callback, fut)
        )
        # 返回的是 CustomFuture
        return future

    def call_soon_threadsafe(self, callback, *args):
        """
        线程安全地将一个回调调度到事件循环中。
        在真实 asyncio 中，会通过 _write_to_self_pipe 或其他机制实现。
        这部分的实现比较复杂。
        """
        # 简化实现：可以在 selector 中注册一个“唤醒 socket”，当线程完成任务后，写入这个 socket，事件循环就会被唤醒
        # TODO
        pass


def _Part_5():
    ...
# ================================ Part-5: CustomTask + 自定义事件循环 构建简单服务器 ================================
def run_custom_event_loop():
    """
    展示如何基于上面的 CustomTask + CustomEventLoop 实现简单服务器。
    对比 asyncio.run() 方法的用法，上面 CustomEventLoop.run() 实现似乎应当把下面
    custom_server() + listen_for_connections() + read_from_client 都放进去才对，
    不过考虑到 asyncio.run() 是最外层的封装，不应当是 CustomEventLoop.run() 里提供实现，所以这里还是分开了。
    """
    async def read_from_client(conn: socket_class, loop: CustomEventLoop) -> None:  # A
        print(f"Reading data from client {conn}")
        try:
            while data := await loop.sock_recv(conn):
                print(f"Got {data} from client!")
        finally:
            loop.sock_close(conn)

    async def listen_for_connections(sock: socket_class, loop: CustomEventLoop):  # B
        while True:
            print(f"[{get_now()}] Waiting for connection...")
            conn, addr = await loop.sock_accept(sock)
            print(f"[{get_now()}] Established connection with client socket: {sock}")
            sock_receive = read_from_client(conn, loop)
            # 原作者的实现如下，因为原本在 CustomTask 的 __init__ 方法里调用了 loop.register_task() 方法，并且忽略了返回的Task对象，后续没用到
            # CustomTask(sock_receive, loop)
            # 这里将 CustomTask.__init__() 中调用 loop.register_task() 的调用移出来了，更加清晰，更贴近 asyncio.create_task() 的风格
            task = CustomTask(sock_receive)
            loop.register_task(task)
            print(f"[{get_now()}] Registering data read task for client socket: {sock}!")

    async def custom_server(loop: CustomEventLoop):
        # 创建&设置服务器socket
        server_socket = socket.socket()
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(SERVER_ADDRESS)
        server_socket.listen()
        server_socket.setblocking(False)

        # 启动服务器
        await listen_for_connections(server_socket, loop)

    event_loop = CustomEventLoop()  # C
    server_coro = custom_server(event_loop)
    event_loop.run(server_coro)


# ================================ main 函数 ================================
def main():
    run_custom_future()
    run_socket_server_with_future()
    run_custom_event_loop()


if __name__ == '__main__':
    main()
