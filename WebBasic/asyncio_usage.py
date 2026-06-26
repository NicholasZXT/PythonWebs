"""
演示asyncio使用
"""
import os
import time
import threading
from typing import TYPE_CHECKING, List, Dict, Tuple, AsyncGenerator, AsyncIterator
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import httpx
import asyncio
from asyncio import ALL_COMPLETED, FIRST_COMPLETED, FIRST_EXCEPTION


async def task_cancel_usage():
    """
    展示如何取消Task执行。

    基本说明：
      - Task.cancel() 会向协程注入 CancelledError 异常，协程可以在 except 中捕获并做清理工作。
      - 取消操作是协作式的：协程必须通过 await 交出控制权，取消才能生效。
      - 如果协程正在执行阻塞IO（如 time.sleep()），取消不会立即生效。
      - 取消一个已完成的 Task 不会报错，返回 False。

    注意事项：
      - 不要在 except CancelledError 中吞掉异常而不重新抛出，否则 Task 不会被标记为已取消。
      - 使用 asyncio.shield() 可以保护关键操作不被取消。

    FAQ：
      Q: task.cancel() 的返回值是什么？是协程的 return 值吗？
      A: 不是。返回 bool，表示取消请求是否成功发出：
         - True：Task 尚未完成，取消信号已成功注入
         - False：Task 已经完成（或已被取消），无法再发送取消请求
         协程的返回值只能通过 await task（正常完成时）或 task.result()（已完成且未取消时）获取。

      Q: CancelledError 是否只有外部通过 await 交出控制权才会触发？触发位置在哪？
      A: task.cancel() 调用后，取消信号立即标记在 Task 上，但 CancelledError 的实际抛出
         发生在该协程下一次 await 交出控制权给事件循环时。
         它不是在任意语句处触发，而是在 await 表达式处抛出。
         如果 try 块中有多个 await，每个 await 都可能是触发点。

      Q: 内部协程捕获 CancelledError 后，为什么必须再次 raise？
      A: 为了让 Task 对象正确标记为"已取消"状态。如果不重新抛出：
         - task.cancelled() 返回 False（伪装成正常完成）
         - await task 不会抛出 CancelledError，而是返回 except 块之后的返回值
         这不是为了让外部"得知已接受取消"，而是让 asyncio 框架正确记录 Task 的终止状态。

      Q: task.cancelled() 的调用限制和返回值是什么？
      A: 没有调用限制，任何时候都可以调用。返回 bool：
         - True：Task 被成功取消（CancelledError 被抛出且未被吞掉）
         - False：Task 未被取消（正常完成、抛出其他异常、或取消尚未生效）
         注意：cancel() 只是发送请求，cancelled() 反映的是取消是否已生效，两者存在时间差。
    """
    async def do_work(name: str, delay: float):
        """模拟一个可被取消的异步任务"""
        try:
            print(f"  [{name}] 开始工作，预计 {delay}s...")
            await asyncio.sleep(delay)  # ← 这里 await 交出控制权时，事件循环注入 CancelledError
            print(f"  [{name}] 工作完成")
            return f"{name}-result"
        except asyncio.CancelledError:  # 多个await时，无法直接知道是哪个 await 触发的
            print(f"  [{name}] 被取消了，正在清理...")
            # 做一些清理工作（如关闭连接、释放资源）
            await asyncio.sleep(0.1)  # 模拟清理耗时
            print(f"  [{name}] 清理完成")
            # 必须要重新抛出，让 Task 正确标记为已取消
            raise

    print("=== task_cancel_usage ===")

    # 示例1：基本取消
    #   - task.cancel() 返回 True 表示取消请求已发出（此时取消尚未生效）
    #   - 随后 await task 交出控制权，事件循环将 CancelledError 注入 do_work 协程
    #   - do_work 在 await asyncio.sleep(delay) 处触发 CancelledError
    #   - except 块中清理后重新 raise，Task 被标记为 CANCELLED
    #   - 外部 await task 收到 CancelledError，task.cancelled() 返回 True
    print("\n--- 示例1：取消一个正在运行的Task ---")
    task = asyncio.create_task(do_work("Task-A", 5))
    await asyncio.sleep(0.5)  # 让Task先跑一会儿
    was_cancelled = task.cancel()
    print(f"  取消请求发送成功: {was_cancelled}")
    try:
        await task
    except asyncio.CancelledError:
        print(f"  Task已取消: task.cancelled()={task.cancelled()}")

    # 示例2：取消已完成的Task（不会报错）
    #   - Task 已经正常完成，cancel() 返回 False
    #   - await task 直接拿到协程的 return 值，不会抛出 CancelledError
    print("\n--- 示例2：取消已完成的Task ---")
    task2 = asyncio.create_task(do_work("Task-B", 0.1))
    await asyncio.sleep(0.3)  # 等待完成
    was_cancelled = task2.cancel()
    print(f"  取消已完成Task: {was_cancelled} (返回False)")
    result = await task2
    print(f"  结果: {result}")

    # 示例3：批量取消多个Task
    #   - 使用 gather(return_exceptions=True) 收集取消结果
    #   - 每个被取消的 Task 在 await 时产生 CancelledError，被 gather 捕获为异常对象
    print("\n--- 示例3：批量取消多个Task ---")
    tasks = [asyncio.create_task(do_work(f"Batch-{i}", 10)) for i in range(3)]
    await asyncio.sleep(0.3)
    for t in tasks:
        t.cancel()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, r in enumerate(results):
        print(f"  Batch-{i}: {type(r).__name__}")
        

async def task_timeout_usage():
    """
    展示Task超时设置。

    基本说明：
      - asyncio.wait_for(aw, timeout) 为协程/Task设置超时时间，超时后抛出 TimeoutError（继承自 CancelledError）。
      - asyncio.timeout(delay) (Python 3.11+) 是异步上下文管理器，超时后抛出 TimeoutError。
      - asyncio.timeout_at(when) 指定绝对时间点超时。

    注意事项：
      - wait_for 超时后，内部协程会被取消（注入 CancelledError），需要做好清理。
      - 如果协程捕获了 CancelledError 但没有重新抛出，wait_for 会一直等到协程结束。
      - 超时后原 Task 仍然存在（只是被取消了），如果之前用 create_task 创建，需要自行处理。
    """
    async def slow_work(name: str, delay: float):
        try:
            print(f"  [{name}] 开始，需要 {delay}s...")
            await asyncio.sleep(delay)
            print(f"  [{name}] 完成")
            return f"{name}-done"
        except asyncio.CancelledError:
            print(f"  [{name}] 被超时取消，清理中...")
            await asyncio.sleep(0.05)
            raise

    print("=== task_timeout_usage ===")

    # 示例1：wait_for 基本使用 - 未超时
    print("\n--- 示例1：wait_for 未超时 ---")
    try:
        result = await asyncio.wait_for(slow_work("Fast", 0.5), timeout=2.0)
        print(f"  结果: {result}")
    except asyncio.TimeoutError:
        print("  超时了（不应该到这里）")

    # 示例2：wait_for 超时
    print("\n--- 示例2：wait_for 超时 ---")
    try:
        result = await asyncio.wait_for(slow_work("Slow", 3.0), timeout=1.0)
        print(f"  结果: {result}")
    except asyncio.TimeoutError:
        print("  任务超时！TimeoutError 被捕获")

    # 示例3：asyncio.timeout() 上下文管理器 (Python 3.11+)
    print("\n--- 示例3：asyncio.timeout() 上下文管理器 ---")
    try:
        async with asyncio.timeout(1.0):
            await slow_work("CtxTask", 3.0)
    except TimeoutError:
        print("  上下文超时！")

    # 示例4：对已创建的Task使用 wait_for
    print("\n--- 示例4：对已创建的Task使用 wait_for ---")
    task = asyncio.create_task(slow_work("TaskTimeout", 5.0))
    try:
        result = await asyncio.wait_for(task, timeout=1.0)
    except asyncio.TimeoutError:
        print(f"  Task超时，task.cancelled()={task.cancelled()}")
        # 注意：此时 task 已被取消，但对象还在
        

async def task_shield_usage():
    """
    展示Task保护屏蔽使用。

    基本说明：
      - asyncio.shield(aw) 保护一个协程不被取消：外部取消操作不会影响被 shield 包裹的协程。
      - shield 返回的是一个 Future-like 对象，取消它不会取消内部协程。
      - 常用于：关键数据写入、事务提交等不可中断的操作。

    注意事项：
      - shield 只保护被包裹的协程不被"外部"取消，如果内部协程自己抛出 CancelledError，仍然会取消。
      - shield 本身不阻止 TimeoutError，wait_for + shield 时，wait_for 超时后 shield 返回的 Future 被取消，
        但内部协程继续运行。需要手动 await 内部协程获取结果。
      - 如果 shield 的 Future 被取消而你仍需要内部协程的结果，必须保留对原始协程/Task 的引用。
    """
    async def critical_work(name: str, delay: float):
        """模拟关键任务（如数据库写入）"""
        try:
            print(f"  [{name}] 关键操作开始...")
            await asyncio.sleep(delay)
            print(f"  [{name}] 关键操作完成")
            return f"{name}-success"
        except asyncio.CancelledError:
            print(f"  [{name}] 关键操作被取消（不应该发生）")
            raise

    print("=== task_shield_usage ===")

    # 示例1：shield 基本使用 - 保护内部协程不被取消
    print("\n--- 示例1：shield 保护协程不被取消 ---")
    inner = critical_work("Protected", 2.0)
    shielded = asyncio.shield(inner)
    # 模拟外部取消
    await asyncio.sleep(0.3)
    shielded.cancel()
    try:
        await shielded
    except asyncio.CancelledError:
        print("  shield 返回的 Future 被取消了...")
    # 但内部协程仍在运行，需要手动等待
    result = await inner
    print(f"  内部协程结果: {result}")

    # 示例2：shield + wait_for - 超时不取消内部任务
    print("\n--- 示例2：shield + wait_for 超时 ---")
    inner2 = critical_work("ShieldTimeout", 3.0)
    try:
        result = await asyncio.wait_for(asyncio.shield(inner2), timeout=1.0)
    except asyncio.TimeoutError:
        print("  wait_for 超时了，但内部任务仍在运行...")
        # 内部任务继续执行，等待它完成
        result = await inner2
        print(f"  内部任务最终结果: {result}")

    # 示例3：不保护的对比
    print("\n--- 示例3：无 shield 保护的对比 ---")
    task = asyncio.create_task(critical_work("Unprotected", 3.0))
    await asyncio.sleep(0.3)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print(f"  无保护Task被取消: task.cancelled()={task.cancelled()}")


async def task_exception_usage():
    """
    展示Task异常处理。

    基本说明：
      - Task 中抛出的异常不会立即传播，而是在 await Task 时才会抛出。
      - 如果不 await 一个抛出异常的 Task，异常会被静默吞掉（仅在 Task 被 GC 时打印日志）。
      - Task.exception() 可以获取 Task 中的异常而不重新抛出。
      - asyncio.gather(return_exceptions=True) 可以将异常作为结果返回。

    注意事项：
      - 一定要 await 被创建的 Task，否则异常可能被静默忽略。
      - 使用 return_exceptions=True 时，需要手动检查每个结果是正常值还是异常对象。
      - 在 Python 3.11+ 中可以使用 ExceptionGroup 处理多个并发异常。

    FAQ：
      Q: Task 抛出的异常，只有外部 await 该 Task 时才能被捕获？
      A: 是的。Task 内部抛出的异常被 Task 对象"暂存"，只有外部 await task 时才会重新抛出。
         如果 create_task 后不 await，异常就像从未发生过（仅在 GC 时可能看到警告日志
         "Task exception was never retrieved"）。

      Q: Task 抛出异常后，await task 能拿到返回值吗？
      A: 不能。await task 在 Task 异常完成时直接抛出异常，不会返回任何值。
         Task 的两种终止状态是互斥的：要么有返回值（task.result() 可用），
         要么有异常（task.exception() 可用），不可能同时存在。

      Q: task.exception() 的返回值是什么？
      A: 取决于 Task 状态：
         - 正常完成（有 return 值）→ 返回 None
         - 抛出异常（如 ValueError）→ 返回该异常对象（不重新抛出）
         - 被取消（CancelledError 且正确 raise）→ 返回 CancelledError 实例
         - 尚未完成 → 抛出 InvalidStateError
         注意：task.exception() 不会重新抛出异常，只是返回异常对象本身，
         这与 await task（会真正抛出异常）完全不同。

      Q: await task / task.result() / task.exception() 三者的区别？
      A: 总结如下：
         ┌──────────────────┬───────────────────┬───────────────────┬──────────────────┐
         │      方法        │    正常完成时      │    异常完成时      │    未完成时       │
         ├──────────────────┼───────────────────┼───────────────────┼──────────────────┤
         │ await task       │ 返回 return 值    │ 抛出异常          │ 阻塞等待          │
         │ task.result()    │ 返回 return 值    │ 抛出异常          │ InvalidStateError │
         │ task.exception() │ 返回 None         │ 返回异常对象(不抛) │ InvalidStateError │
         └──────────────────┴───────────────────┴───────────────────┴──────────────────┘
    """
    async def work_success(name: str, delay: float):
        await asyncio.sleep(delay)
        return f"{name}-ok"

    async def work_fail(name: str, delay: float):
        await asyncio.sleep(delay)
        raise ValueError(f"{name} 出错了！")

    print("=== task_exception_usage ===")

    # 示例1：await Task 时异常传播
    #   - Task 内部抛出的异常被暂存，不会立即传播
    #   - 只有 await task 时，异常才会被重新抛出
    #   - await task 在异常完成时直接抛异常，不会返回任何值（result 变量不会被赋值）
    #   - 异常被捕获后，task.exception() 返回该异常对象（不重新抛出）
    print("\n--- 示例1：await Task 时异常传播 ---")
    task = asyncio.create_task(work_fail("FailTask", 0.3))
    try:
        await task  # ← 这里直接抛出 ValueError，不会返回任何值
    except ValueError as e:
        print(f"  捕获到异常: {e}")
    print(f"  task.exception(): {task.exception()}")  # 返回异常对象，不抛出

    # 示例2：使用 task.exception() 检查异常（不重新抛出）
    #   - task.exception() 不会抛出异常，只返回异常对象或 None
    #   - 正常完成时返回 None，异常完成时返回异常对象
    #   - 注意：必须在 Task 完成后才能调用，否则抛出 InvalidStateError
    print("\n--- 示例2：task.exception() 检查异常 ---")
    task2 = asyncio.create_task(work_fail("CheckTask", 0.2))
    await asyncio.sleep(0.5)  # 等待完成（不 await task2，异常不会传播）
    exc = task2.exception()  # 获取异常对象，不抛出
    if exc:
        print(f"  Task 异常: {type(exc).__name__}: {exc}")
    else:
        print(f"  Task 正常完成: {task2.result()}")

    # 示例3：gather 的 return_exceptions=True
    #   - 异常不会传播，而是作为结果列表中的元素返回
    #   - 需要手动 isinstance(r, Exception) 区分正常结果和异常
    print("\n--- 示例3：gather return_exceptions=True ---")
    results = await asyncio.gather(
        work_success("Good", 0.2),
        work_fail("Bad", 0.3),
        work_success("AlsoGood", 0.1),
        return_exceptions=True,
    )
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            print(f"  结果[{i}]: 异常 -> {type(r).__name__}: {r}")
        else:
            print(f"  结果[{i}]: 正常 -> {r}")

    # 示例4：gather 默认行为 - 第一个异常即传播
    #   - 不设置 return_exceptions 时，第一个异常会立即传播
    #   - 其余未完成的 Task 会被自动取消
    print("\n--- 示例4：gather 默认行为（异常立即传播） ---")
    try:
        await asyncio.gather(
            work_success("G1", 0.2),
            work_fail("G2", 0.1),  # 这个先失败
            work_success("G3", 0.5),  # 这个会被取消
        )
    except ValueError as e:
        print(f"  捕获到: {e}")
        print("  G3 可能已被取消（因为 gather 在第一个异常时取消其余Task）")


async def asnyc_with_context_usage():
    """
    展示异步with上下文使用。

    基本说明：
      - async with 用于异步上下文管理器，其 __aenter__ 和 __aexit__ 都是协程。
      - 常用于：异步数据库连接、异步文件操作、异步锁等需要异步初始化和清理的场景。
      - 与同步 with 的区别：__aenter__/__aexit__ 中可以 await 其他协程。

    注意事项：
      - 必须在 async 函数中使用 async with。
      - __aexit__ 中的异常处理与同步 with 一致：返回 True 可吞掉异常。
      - asyncio 内置了多种异步上下文管理器：asyncio.Lock、asyncio.Semaphore、asyncio.timeout 等。
    """
    # 自定义异步上下文管理器
    class AsyncResource:
        """模拟一个需要异步打开和关闭的资源（如数据库连接）"""
        def __init__(self, name: str):
            self.name = name

        async def __aenter__(self):
            print(f"  [{self.name}] 正在异步打开资源...")
            await asyncio.sleep(0.3)  # 模拟异步连接
            print(f"  [{self.name}] 资源已打开")
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            print(f"  [{self.name}] 正在异步关闭资源...")
            await asyncio.sleep(0.2)  # 模拟异步清理
            print(f"  [{self.name}] 资源已关闭")
            # 返回 False（默认）表示不吞掉异常
            return False

        async def do_something(self):
            print(f"  [{self.name}] 执行操作...")
            await asyncio.sleep(0.2)
            return f"{self.name}-data"

    print("=== asnyc_with_context_usage ===")

    # 示例1：基本 async with 使用
    print("\n--- 示例1：基本 async with ---")
    async with AsyncResource("DB-Conn") as res:
        data = await res.do_something()
        print(f"  获取数据: {data}")
    print("  async with 块结束")

    # 示例2：async with 中的异常处理
    print("\n--- 示例2：async with 中的异常 ---")
    try:
        async with AsyncResource("FailConn") as res:
            await res.do_something()
            raise RuntimeError("模拟操作异常")
    except RuntimeError as e:
        print(f"  捕获异常: {e}")
        print("  注意：即使发生异常，__aexit__ 仍然被调用（资源被正确关闭）")

    # 示例3：嵌套多个 async with
    print("\n--- 示例3：嵌套多个 async with ---")
    async with AsyncResource("Res-A") as a, AsyncResource("Res-B") as b:
        data_a = await a.do_something()
        data_b = await b.do_something()
        print(f"  结果: {data_a}, {data_b}")

    # 示例4：asyncio.Lock 异步锁
    print("\n--- 示例4：asyncio.Lock 异步锁 ---")
    lock = asyncio.Lock()
    shared_counter = 0

    async def locked_increment(name: str):
        nonlocal shared_counter
        async with lock:
            print(f"  [{name}] 获取锁，当前值: {shared_counter}")
            current = shared_counter
            await asyncio.sleep(0.1)  # 模拟处理
            shared_counter = current + 1
            print(f"  [{name}] 释放锁，新值: {shared_counter}")

    await asyncio.gather(
        locked_increment("Worker-1"),
        locked_increment("Worker-2"),
        locked_increment("Worker-3"),
    )
    print(f"  最终值: {shared_counter}")

    # 示例5：asyncio.Semaphore 信号量（限制并发数）
    print("\n--- 示例5：asyncio.Semaphore 限制并发 ---")
    semaphore = asyncio.Semaphore(2)  # 最多2个并发

    async def limited_task(name: str, delay: float):
        async with semaphore:
            print(f"  [{name}] 开始 (信号量获取)")
            await asyncio.sleep(delay)
            print(f"  [{name}] 完成 (信号量释放)")

    await asyncio.gather(
        limited_task("S1", 0.5),
        limited_task("S2", 0.5),
        limited_task("S3", 0.3),
        limited_task("S4", 0.3),
    )
    print("  所有信号量任务完成")
    

async def gather_usage():
    """
    展示asyncio.gather()并发执行多个Task的基本使用。

    基本说明：
      - asyncio.gather(*aws) 并发执行多个协程/Task，返回一个列表，结果顺序与传入顺序一致。
      - 所有协程会被自动封装为 Task 并加入事件循环。
      - gather 本身返回一个 Future，可以 await 获取结果。

    注意事项：
      - 默认情况下，任意一个子任务抛出异常，gather 会立即传播该异常，并取消其余未完成的子任务。
      - 设置 return_exceptions=True 后，异常会作为结果列表中的元素返回，不会传播。
      - gather 的结果顺序始终与传入顺序一致，与各任务完成先后无关。
      - 如果需要超时控制，需配合 asyncio.wait_for 使用。
    """
    async def fetch_data(name: str, delay: float):
        """模拟异步获取数据"""
        print(f"  [{name}] 开始获取数据...")
        await asyncio.sleep(delay)
        print(f"  [{name}] 数据获取完成")
        return f"{name}-data"

    async def fetch_with_error(name: str, delay: float):
        """模拟异步获取数据时出错"""
        print(f"  [{name}] 开始获取数据...")
        await asyncio.sleep(delay)
        raise RuntimeError(f"{name} 获取失败")

    print("=== gather_usage ===")

    # 示例1：gather 基本使用 - 结果顺序与传入顺序一致
    print("\n--- 示例1：gather 基本使用 ---")
    results = await asyncio.gather(
        fetch_data("API-A", 0.5),
        fetch_data("API-B", 0.2),  # 这个先完成
        fetch_data("API-C", 0.3),
    )
    print(f"  结果顺序: {results}")
    print("  注意：API-B 先完成，但结果仍在索引1的位置")

    # 示例2：gather 异常处理 - 默认行为
    print("\n--- 示例2：gather 默认异常处理 ---")
    try:
        await asyncio.gather(
            fetch_data("Good", 0.3),
            fetch_with_error("Bad", 0.1),  # 先失败
            fetch_data("Cancelled", 0.5),  # 会被取消
        )
    except RuntimeError as e:
        print(f"  捕获异常: {e}")
        print("  注意：'Cancelled' 任务被取消了")

    # 示例3：gather return_exceptions=True
    print("\n--- 示例3：gather return_exceptions=True ---")
    results = await asyncio.gather(
        fetch_data("G1", 0.3),
        fetch_with_error("G2", 0.2),
        fetch_data("G3", 0.1),
        return_exceptions=True,
    )
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            print(f"  结果[{i}]: 异常 -> {r}")
        else:
            print(f"  结果[{i}]: 正常 -> {r}")

    # 示例4：gather + wait_for 超时控制
    print("\n--- 示例4：gather + wait_for 超时 ---")
    try:
        results = await asyncio.wait_for(
            asyncio.gather(
                fetch_data("T1", 0.3),
                fetch_data("T2", 3.0),  # 这个太慢
            ),
            timeout=1.0,
        )
    except asyncio.TimeoutError:
        print("  gather 整体超时！")


async def as_complete_usage():
    """
    展示asyncio.as_completed()等待多个Task的基本使用。

    基本说明：
      - asyncio.as_completed(aws, *, timeout=None) 返回一个异步迭代器，按任务完成顺序逐个产出结果。
      - 与 gather 不同，as_completed 不保证结果顺序，哪个先完成就先返回哪个。
      - 适用于：需要尽快处理每个结果（如流式处理、先到先服务）的场景。

    注意事项：
      - as_completed 返回的是异步迭代器，必须使用 async for 遍历。
      - 如果某个任务抛出异常，async for 迭代到它时才会抛出。
      - 超时后，未完成的任务会被取消。
      - 无法直接知道每个结果对应哪个原始任务，需要自行维护映射关系。
    """
    async def fetch(name: str, delay: float):
        print(f"  [{name}] 开始 (delay={delay}s)...")
        await asyncio.sleep(delay)
        print(f"  [{name}] 完成")
        return f"{name}-result"

    async def fetch_error(name: str, delay: float):
        print(f"  [{name}] 开始 (delay={delay}s)...")
        await asyncio.sleep(delay)
        raise RuntimeError(f"{name} 失败")

    print("=== as_complete_usage ===")

    # 示例1：as_completed 基本使用 - 按完成顺序返回
    print("\n--- 示例1：as_completed 基本使用 ---")
    tasks = [
        fetch("Slow", 0.5),
        fetch("Fast", 0.1),
        fetch("Medium", 0.3),
    ]
    for coro in asyncio.as_completed(tasks):
        result = await coro
        print(f"  -> 获得结果: {result}")
    print("  注意：Fast 先完成，所以先返回")

    # 示例2：as_completed 异常处理
    print("\n--- 示例2：as_completed 异常处理 ---")
    tasks2 = [
        fetch("Good1", 0.3),
        fetch_error("Bad", 0.1),  # 先完成但会失败
        fetch("Good2", 0.5),
    ]
    for coro in asyncio.as_completed(tasks2):
        try:
            result = await coro
            print(f"  -> 获得结果: {result}")
        except RuntimeError as e:
            print(f"  -> 捕获异常: {e}")

    # 示例3：as_completed 超时
    print("\n--- 示例3：as_completed 超时 ---")
    tasks3 = [
        fetch("Quick", 0.2),
        fetch("Long", 5.0),
    ]
    try:
        for coro in asyncio.as_completed(tasks3, timeout=1.0):
            result = await coro
            print(f"  -> 获得结果: {result}")
    except asyncio.TimeoutError:
        print("  as_completed 超时！未完成的任务被取消")

    # 示例4：使用字典维护任务-结果映射
    print("\n--- 示例4：维护任务-结果映射 ---")
    task_map = {
        asyncio.ensure_future(fetch("User", 0.3)): "UserAPI",
        asyncio.ensure_future(fetch("Order", 0.1)): "OrderAPI",
        asyncio.ensure_future(fetch("Product", 0.2)): "ProductAPI",
    }
    for done_task in asyncio.as_completed(task_map.keys()):
        api_name = task_map[done_task]
        result = await done_task
        print(f"  {api_name} -> {result}")


async def wait_usage():
    """
    展示asyncio.wait()等待多个Task的基本使用。

    基本说明：
      - asyncio.wait(aws, *, timeout=None, return_when=ALL_COMPLETED) 等待一组 Task 完成。
      - 返回 (done, pending) 两个集合：done 是已完成的 Task，pending 是未完成的 Task。
      - return_when 参数控制返回时机：
        * ALL_COMPLETED（默认）：所有 Task 完成或超时
        * FIRST_COMPLETED：第一个 Task 完成或超时
        * FIRST_EXCEPTION：第一个异常发生或所有完成

    注意事项：
      - wait 不会取消 pending 中的 Task，需要手动处理。
      - wait 不会自动传播异常，需要从 done 中的 Task 手动获取。
      - 与 gather 不同，wait 接受的是 Task/Future 集合，不会自动封装协程。
      - 传入协程对象会被自动包装为 Task，但推荐显式使用 create_task。
    """
    async def work(name: str, delay: float):
        print(f"  [{name}] 开始...")
        await asyncio.sleep(delay)
        print(f"  [{name}] 完成")
        return f"{name}-done"

    async def work_error(name: str, delay: float):
        print(f"  [{name}] 开始...")
        await asyncio.sleep(delay)
        raise RuntimeError(f"{name} 出错")

    print("=== wait_usage ===")

    # 示例1：wait 基本使用 - ALL_COMPLETED
    print("\n--- 示例1：wait ALL_COMPLETED ---")
    tasks = [asyncio.create_task(work(f"W{i}", 0.2 * i)) for i in range(1, 4)]
    done, pending = await asyncio.wait(tasks, return_when=ALL_COMPLETED)
    print(f"  完成: {len(done)} 个, 未完成: {len(pending)} 个")
    for t in done:
        print(f"  -> {t.result()}")

    # 示例2：wait FIRST_COMPLETED
    print("\n--- 示例2：wait FIRST_COMPLETED ---")
    tasks2 = [
        asyncio.create_task(work("Slow", 1.0)),
        asyncio.create_task(work("Fast", 0.2)),
        asyncio.create_task(work("Medium", 0.5)),
    ]
    done, pending = await asyncio.wait(tasks2, return_when=FIRST_COMPLETED)
    print(f"  第一个完成: {len(done)} 个, 剩余: {len(pending)} 个")
    for t in done:
        print(f"  -> {t.result()}")
    # 取消剩余任务
    for t in pending:
        t.cancel()
    print("  已取消剩余任务")

    # 示例3：wait FIRST_EXCEPTION
    print("\n--- 示例3：wait FIRST_EXCEPTION ---")
    tasks3 = [
        asyncio.create_task(work("Normal", 0.5)),
        asyncio.create_task(work_error("Bad", 0.1)),  # 先出错
        asyncio.create_task(work("AlsoNormal", 0.8)),
    ]
    done, pending = await asyncio.wait(tasks3, return_when=FIRST_EXCEPTION)
    print(f"  完成/异常: {len(done)} 个, 剩余: {len(pending)} 个")
    for t in done:
        if t.exception():
            print(f"  -> 异常: {t.exception()}")
        else:
            print(f"  -> 结果: {t.result()}")
    for t in pending:
        t.cancel()

    # 示例4：wait 超时
    print("\n--- 示例4：wait 超时 ---")
    tasks4 = [
        asyncio.create_task(work("Quick", 0.3)),
        asyncio.create_task(work("Long", 5.0)),
    ]
    done, pending = await asyncio.wait(tasks4, timeout=1.0)
    print(f"  超时后 - 完成: {len(done)} 个, 未完成: {len(pending)} 个")
    for t in done:
        print(f"  -> {t.result()}")
    for t in pending:
        print(f"  -> 取消: {t.get_name()}")
        t.cancel()
        

async def run_in_executor_usage():
    """
    展示asyncio.loop.run_in_executor()对接线程池/进程池的使用。

    基本说明：
      - loop.run_in_executor(executor, func, *args) 在线程池/进程池中执行阻塞函数，返回可 await 的 Future。
      - 用于将 CPU 密集型或阻塞 IO 操作（如同步文件读写、requests 库调用）放到线程/进程中执行，避免阻塞事件循环。
      - 默认使用 ThreadPoolExecutor（默认线程数：min(32, os.cpu_count() + 4)）。

    注意事项：
      - 线程池适合 IO 密集型阻塞操作（如 requests、同步文件读写）。
      - 进程池适合 CPU 密集型操作（如大量计算），但进程间通信有序列化开销。
      - 不要在线程池中修改 asyncio 对象（如 Task、Future），它们不是线程安全的。
      - 可以使用 asyncio.to_thread() (Python 3.9+) 作为 run_in_executor 的便捷封装。
    """
    import time

    def blocking_io_work(name: str, delay: float):
        """模拟阻塞IO操作（如 requests.get、同步文件读写）"""
        print(f"  [{name}] 阻塞IO开始 (线程: {threading.current_thread().name})...")
        time.sleep(delay)  # 阻塞 sleep，不是 asyncio.sleep
        print(f"  [{name}] 阻塞IO完成")
        return f"{name}-io-result"

    def cpu_intensive_work(n: int):
        """模拟CPU密集型操作"""
        print(f"  [CPU-{n}] 计算开始 (线程: {threading.current_thread().name})...")
        total = sum(i * i for i in range(n * 1_000_000))
        print(f"  [CPU-{n}] 计算完成")
        return total

    print("=== run_in_executor_usage ===")

    loop = asyncio.get_running_loop()

    # 示例1：使用默认线程池执行阻塞IO
    print("\n--- 示例1：默认线程池执行阻塞IO ---")
    result = await loop.run_in_executor(None, blocking_io_work, "IO-Task", 1.0)
    print(f"  结果: {result}")

    # 示例2：并发执行多个阻塞IO任务
    print("\n--- 示例2：并发执行多个阻塞IO ---")
    tasks = [
        loop.run_in_executor(None, blocking_io_work, f"IO-{i}", 0.5)
        for i in range(3)
    ]
    results = await asyncio.gather(*tasks)
    print(f"  所有IO结果: {results}")
    print("  注意：3个阻塞任务在3个线程中并发执行，总耗时约0.5s而非1.5s")

    # 示例3：使用自定义线程池
    print("\n--- 示例3：自定义线程池 ---")
    with ThreadPoolExecutor(max_workers=2) as pool:
        tasks2 = [
            loop.run_in_executor(pool, blocking_io_work, f"Custom-{i}", 0.3)
            for i in range(4)
        ]
        results2 = await asyncio.gather(*tasks2)
        print(f"  自定义线程池结果: {results2}")
        print("  注意：max_workers=2，4个任务分两批执行")

    # 示例4：使用进程池执行CPU密集型任务
    print("\n--- 示例4：进程池执行CPU密集型 ---")
    with ProcessPoolExecutor(max_workers=2) as proc_pool:
        tasks3 = [
            loop.run_in_executor(proc_pool, cpu_intensive_work, n)
            for n in [5, 8, 3]
        ]
        results3 = await asyncio.gather(*tasks3)
        print(f"  CPU计算结果: {[r for r in results3]}")

    # 示例5：asyncio.to_thread() 便捷方法 (Python 3.9+)
    print("\n--- 示例5：asyncio.to_thread() ---")
    result = await asyncio.to_thread(blocking_io_work, "ToThread", 0.5)
    print(f"  to_thread 结果: {result}")
    print("  注意：asyncio.to_thread() 内部就是调用 run_in_executor(None, ...)")

    # 示例6：对比 - 如果在协程中直接调用阻塞函数会怎样
    print("\n--- 示例6：对比 - 协程中直接调用阻塞函数 ---")
    start = time.time()
    # 错误做法：在协程中直接调用 time.sleep（会阻塞整个事件循环）
    # 这里仅做演示，实际不要这样做
    blocking_io_work("DirectCall", 0.3)
    blocking_io_work("DirectCall2", 0.3)
    print(f"  直接调用总耗时: {time.time() - start:.2f}s (串行阻塞)")
    print("  正确做法应使用 run_in_executor 或 asyncio.to_thread")


async def main():
    """调试入口函数"""
    await task_cancel_usage()
    await task_timeout_usage()
    await task_shield_usage()
    await task_exception_usage()
    await asnyc_with_context_usage()
    await gather_usage()
    await as_complete_usage()
    await wait_usage()
    await run_in_executor_usage()
    

if __name__ == "__main__":
    asyncio.run(main())
