"""
asyncio使用总结
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

    print("\n\n=== task_timeout_usage ===")

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

    # 示例3：asyncio.timeout() / wait_for 超时控制
    #   - Python 3.11+ 可用 asyncio.timeout(delay) 上下文管理器，语法更简洁：
    #       async with asyncio.timeout(1.0):
    #           await slow_work("CtxTask", 3.0)
    #   - 兼容旧版本：使用 asyncio.wait_for() 包装，效果相同
    print("\n--- 示例3：超时控制（wait_for 版本，兼容 Python 3.7+） ---")
    try:
        await asyncio.wait_for(slow_work("CtxTask", 3.0), timeout=1.0)
    except asyncio.TimeoutError:
        print("  超时！TimeoutError 被捕获")

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
      - ⚠️ 坑：shield() 内部会 await 传入的对象。如果传入裸协程，后续不能再 await 它
        （RuntimeError: coroutine is being awaited already）。正确做法：先 create_task() 再传 Task。
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

    print("\n\n=== task_shield_usage ===")

    # 示例1：shield 基本使用 - 保护内部协程不被取消
    #   - 关键：shield() 内部会 await 传入的对象，如果是裸协程则不能再次 await
    #   - 正确做法：先用 create_task() 创建 Task，再传给 shield()
    #   - Task 可以被多次 await，裸协程只能 await 一次
    print("\n--- 示例1：shield 保护协程不被取消 ---")
    inner_task = asyncio.create_task(critical_work("Protected", 2.0))
    shielded = asyncio.shield(inner_task)  # 传入 Task 而非裸协程
    # 模拟外部取消
    await asyncio.sleep(0.3)
    shielded.cancel()
    try:
        await shielded
    except asyncio.CancelledError:
        print("  shield 返回的 Future 被取消了...")
    # 但内部 Task 仍在运行，需要手动等待（Task 可多次 await）
    result = await inner_task
    print(f"  内部协程结果: {result}")

    # 示例2：shield + wait_for - 超时不取消内部任务
    #   - 同样需要先 create_task，否则 wait_for 内部的 shield 会消耗掉裸协程
    print("\n--- 示例2：shield + wait_for 超时 ---")
    inner_task2 = asyncio.create_task(critical_work("ShieldTimeout", 3.0))
    try:
        result = await asyncio.wait_for(asyncio.shield(inner_task2), timeout=1.0)
    except asyncio.TimeoutError:
        print("  wait_for 超时了，但内部任务仍在运行...")
        # 内部任务继续执行，等待它完成（Task 可多次 await）
        result = await inner_task2
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

    print("\n\n=== task_exception_usage ===")

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

    # 示例4：gather 默认行为 - 第一个异常即传播（⚠️ 深坑！）
    #   - 不设置 return_exceptions 时，第一个异常会立即传播
    #   - 关键：其余 Task **不会被取消**，继续在后台运行，结果被静默丢弃
    #   - 如果后台任务有副作用（写库等），会造成数据不一致
    #   - ⚠️ 输出交叠：G3 的完成消息可能会混入后续 asnyc_with_context_usage() 的输出中
    print("\n--- 示例4：gather 默认行为（异常立即传播） ---")
    try:
        await asyncio.gather(
            work_success("G1", 0.2),
            work_fail("G2", 0.1),  # 这个先失败
            work_success("G3", 0.5),  # 不会被取消！完成输出可能会混入后续示例
        )
    except ValueError as e:
        print(f"  捕获到: {e}")
        print("  G3 继续在后台运行，完成消息可能混入后续示例的输出中")


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

    print("\n\n=== asnyc_with_context_usage ===")

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
      - 默认情况下，某个子任务抛出异常后，该异常立即传播给 await gather() 的协程，
        但其他子任务**不会被取消**，会继续在后台运行（结果被静默丢弃）。
        这是 gather() 最大的坑点：后台任务可能产生副作用（如写入数据库）但无人感知。
      - 设置 return_exceptions=True 后，异常会作为结果列表中的元素返回，不会传播。
      - gather 的结果顺序始终与传入顺序一致，与各任务完成先后无关。
      - 如果需要超时控制，需配合 asyncio.wait_for 使用。

    FAQ：
      Q: await asyncio.gather() 是否类似阻塞等待？
      A: 是的。await gather() 会暂停当前协程，直到所有子任务完成（或异常/超时），
         然后一次性返回所有结果。但它阻塞的是当前协程，不是整个事件循环。
         子任务之间是并发执行的，总耗时 ≈ max(各子任务耗时)，而非 sum。
         对比：as_completed() 是先完成先返回，wait() 可控制返回时机。

      Q: 某个子任务异常后，其他子任务会被取消吗？
      A: **不会！** 根据官方文档，异常传播后其他子任务继续在后台运行，不会被取消。
         这与 as_completed() 的行为一致（异常不影响其他任务），但与许多人的直觉相反。
         危险之处：后台任务可能正在写数据库、发送请求等，但结果被静默丢弃。
         如果需要"一个失败就取消其余"的行为，应使用 asyncio.TaskGroup (Python 3.11+)。

      ⚠️ 深坑警告：孤儿任务的输出会与后续代码的输出交叠在一起！
      由于 gather 异常传播后当前协程继续执行后面的代码，而"孤儿"Task 仍在后台运行，
      它们的 print 输出会交错出现在后续示例的输出之中，让人误以为任务被取消了。
      实际上它们执行完了，只是输出混在了后面。验证方法：在 except 块后加一个
      `await asyncio.sleep(足够长)` 让孤儿任务有独立的输出窗口。

      Q: return_exceptions=True 时，结果是返回值和异常混合的吗？
      A: 是的。结果列表中每个元素要么是正常返回值，要么是异常对象（包括 CancelledError）。
         需要手动 isinstance(r, Exception) 区分。结果顺序始终与传入顺序一致，
         所以可以通过索引知道哪个子任务对应哪个结果。
         如果不设置 return_exceptions=True，第一个异常就会传播，根本拿不到结果列表。

      Q: gather() 默认 vs return_exceptions=True 的区别？
      A: 总结如下：
         ┌────────────────────────────┬──────────────────────────────┐
         │  gather() 默认             │  gather(return_exceptions=True) │
         ├────────────────────────────┼──────────────────────────────┤
         │  返回时机：全部完成或首个异常 │  返回时机：全部完成             │
         │  异常行为：立即传播         │  异常行为：作为结果列表元素返回   │
         │  其他任务：继续运行(结果丢弃)│  其他任务：继续运行(结果保留)    │
         │  结果内容：正常返回值列表    │  结果内容：返回值+异常对象混合列表 │
         │  结果顺序：与传入顺序一致    │  结果顺序：与传入顺序一致         │
         └────────────────────────────┴──────────────────────────────┘
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

    print("\n\n=== gather_usage ===")

    # 示例1：gather 基本使用 - 结果顺序与传入顺序一致
    #   - await gather() 暂停当前协程，等所有子任务完成后一次性返回
    #   - 子任务并发执行，总耗时 ≈ max(0.5, 0.2, 0.3) = 0.5s，而非 1.0s
    #   - 结果顺序始终与传入顺序一致，即使 API-B 先完成也在索引1
    print("\n--- 示例1：gather 基本使用 ---")
    results = await asyncio.gather(
        fetch_data("API-A", 0.5),
        fetch_data("API-B", 0.2),  # 这个先完成
        fetch_data("API-C", 0.3),
    )
    print(f"  结果顺序: {results}")
    print("  注意：API-B 先完成，但结果仍在索引1的位置")

    # 示例2：gather 异常处理 - 默认行为（⚠️ 最大深坑！）
    #   - Bad 在 0.1s 后抛出异常，gather 立即传播该异常
    #   - 关键：其他子任务**不会被取消**，继续在后台运行！
    #   - 此处 Good(0.3s) 和 Cancelled(0.5s) 会继续执行完毕，但结果被静默丢弃
    #
    #   ⚠️ 输出交叠陷阱（坑中之坑！）：
    #   你会发现只看到 "[Good] 开始..." "[Cancelled] 开始..." 但没有看到它们的完成输出。
    #   这不是因为它们被取消了！而是因为：
    #   - t=0.1s: Bad 抛异常 → except 块执行 → 打印"捕获异常..."
    #   - t=0.1s 之后: 代码继续执行示例3、示例4...
    #   - t=0.3s: Good 完成 → "[Good] 数据获取完成" 混在示例3的输出中！
    #   - t=0.5s: Cancelled 完成 → "[Cancelled] 数据获取完成" 混在示例4的输出中！
    #   两个"完成"消息被淹没在后续输出里，造成"被取消"的假象。
    #   验证方法：在 except 块后加 `await asyncio.sleep(2.0)` 让孤儿任务单独输出。
    #
    #   如果这些后台任务有副作用（写库、发请求），它们会静默执行，造成数据不一致！
    print("\n--- 示例2：gather 默认异常处理 ---")
    try:
        await asyncio.gather(
            fetch_data("Good", 0.3),
            fetch_with_error("Bad", 0.1),  # 先失败
            fetch_data("Cancelled", 0.5),  # 不会被取消！继续运行但结果丢弃
        )
    except RuntimeError as e:
        print(f"  捕获异常: {e}")
        # 此处 Good 和 Cancelled 仍在后台运行中！
        # 它们的完成输出可能混入后续示例（示例3、示例4）的输出中
        print("  注意：'Cancelled' 任务继续在后台运行，其输出将混入后续示例中")

    # 示例3：gather return_exceptions=True
    #   - 异常不传播，作为结果列表元素返回，与正常返回值混合在一起
    #   - 必须手动 isinstance(r, Exception) 区分正常结果和异常
    #   - 结果顺序与传入顺序一致，可通过索引对应原始子任务
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
    #   - gather 本身不支持 timeout 参数，需配合 wait_for 使用
    #   - 超时后 gather 内部所有未完成的子任务被取消
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
      - ⚠️ 坑：as_completed yield 的是内部 _wait_for_one 协程，不是传入的原始 Task！
        不能用原始 Task 作为字典 key 来反查。正确做法是用包装函数绑定标识。

    FAQ：
      Q: as_completed() 返回的具体是什么类型？
      A: 返回一个异步迭代器（async iterator），实现了 __aiter__ 和 __anext__ 协议。
         它不是列表、不是 Future、不是 Task。每次 async for 迭代时，__anext__()
         内部会等待下一个完成的 Task，然后产出该 Task 对应的 Future/协程对象。
         它本身不存储所有结果，而是"按完成顺序逐个产出"。

      Q: 遍历时会不会"卡顿"？停顿出现在哪里？
      A: 会的。停顿发生在 async for ... in as_completed() 这一行（即每次迭代的 __anext__() 调用处），
         而不是循环体内的 await coro 处。因为 async for 每次迭代都在等待下一个 Task 完成，
         而进入循环体时 coro 已经完成了，所以 await coro 几乎立即返回。
         如果两个 Task 完成时间接近，async for 几乎立即返回下一个，不会有明显停顿。

      Q: 单个 Task 异常是否影响其他 Task？
      A: 不影响。这是 as_completed() 与 gather() 的重要区别：
         - as_completed：单个异常仅在该 Task 被迭代到时抛出，其他 Task 继续执行
         - gather() 默认：单个异常立即传播，但其他 Task 继续运行（结果被静默丢弃）
         超时情况：as_completed(timeout=...) 超时后抛出 TimeoutError，未完成的任务被取消，
         但已完成的不受影响。

      Q: as_completed() vs gather() 对比？
      A: 总结如下：
         ┌──────────────────┬────────────────────────────┬──────────────────────────┐
         │      特性         │       gather()             │     as_completed()       │
         ├──────────────────┼────────────────────────────┼──────────────────────────┤
         │  返回类型         │  Future（await 后得 list）  │  异步迭代器               │
         │  结果顺序         │  与传入顺序一致             │  按完成顺序               │
         │  返回时机         │  全部完成后一次性返回       │  逐个返回                 │
         │  单个异常         │  传播异常，其他继续运行  │  仅迭代到时抛出，不影响其他 │
         │  停顿位置         │  await gather() 处         │  async for 每次迭代处     │
         └──────────────────┴────────────────────────────┴──────────────────────────┘
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

    print("\n\n=== as_complete_usage ===")

    # 示例1：as_completed 基本使用 - 按完成顺序返回
    #   - as_completed() 返回异步迭代器，async for 每次迭代等待下一个完成的 Task
    #   - 停顿发生在 async for 处（__anext__() 内部等待），而非循环体内的 await coro
    #   - 进入循环体时 coro 已完成，await coro 几乎立即返回
    #   - 时间线：t=0.1 Fast完成 → t=0.3 Medium完成 → t=0.5 Slow完成
    print("\n--- 示例1：as_completed 基本使用 ---")
    tasks = [
        fetch("Slow", 0.5),
        fetch("Fast", 0.1),
        fetch("Medium", 0.3),
    ]
    for coro in asyncio.as_completed(tasks):
        # ↑ async for 在这里等待下一个完成的 Task（可能停顿）
        result = await coro  # ← coro 已完成，几乎不等待
        print(f"  -> 获得结果: {result}")
    print("  注意：Fast 先完成，所以先返回")

    # 示例2：as_completed 异常处理
    #   - Bad 先完成但抛异常，仅在迭代到它时抛出，不影响 Good2 继续执行
    #   - 这与 gather() 不同：gather() 默认传播异常但其他Task继续运行（结果丢弃）
    print("\n--- 示例2：as_completed 异常处理 ---")
    tasks2 = [
        fetch("Good1", 0.3),
        fetch_error("Bad", 0.1),  # 先完成但会失败，不影响 Good2
        fetch("Good2", 0.5),
    ]
    for coro in asyncio.as_completed(tasks2):
        try:
            result = await coro
            print(f"  -> 获得结果: {result}")
        except RuntimeError as e:
            print(f"  -> 捕获异常: {e}")
    print("  注意：Bad 的异常不影响 Good2 继续执行")

    # 示例3：as_completed 超时
    #   - timeout 参数控制整体超时，超时后抛出 TimeoutError
    #   - 已完成的 Task 结果不受影响，未完成的被取消
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

    # 示例4：使用包装函数维护任务-结果映射
    #   - as_completed 不保留传入顺序，需自行维护映射关系
    #   - 坑：as_completed 内部 yield 的是 _wait_for_one 协程，不是原始 Task！
    #     不能用原始 Task 作为字典 key 来查找（会 KeyError）
    #   - 正确做法：用包装函数把 Task 和名称绑定，await 后同时拿到名称和结果
    print("\n--- 示例4：维护任务-结果映射 ---")
    async def wrap(task, api_name: str):
        """包装函数：将 Task 和名称绑定，await 后返回 (名称, 结果)"""
        result = await task
        return api_name, result

    wrapped_tasks = [
        wrap(fetch("User", 0.3), "UserAPI"),
        wrap(fetch("Order", 0.1), "OrderAPI"),
        wrap(fetch("Product", 0.2), "ProductAPI"),
    ]
    for coro in asyncio.as_completed(wrapped_tasks):
        api_name, result = await coro
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

    典型使用场景：
      - 需要知道"哪些完成了、哪些还没完成"（超时后处理 pending）
      - 竞速场景：FIRST_COMPLETED 模式，多个数据源谁先返回用谁的
      - 快速失败：FIRST_EXCEPTION 模式，任何一个出错就立即停止
      - 需要操作原始 Task 对象（调用 result()/exception()/cancel()/get_name() 等）
      - 动态添加/移除任务（wait 接受集合，可运行时增删）
    
    wait() vs gather() vs as_completed() 选择指南：
    | 需求                              | 推荐                             |
    | --------------------------------- | -------------------------------- |
    | 全部完成，按传入顺序拿结果        | `gather()`                       |
    | 全部完成，但需要容忍部分失败      | `gather(return_exceptions=True)` |
    | 先完成先处理，逐个消费            | `as_completed()`                 |
    | 只需要第一个结果（竞速）          | `wait(FIRST_COMPLETED)`          |
    | 任何一个失败就停止                | `wait(FIRST_EXCEPTION)`          |
    | 需要知道哪些没完成、操作原始 Task | `wait()`                         |
    | 超时后需要处理未完成的任务        | `wait(timeout=...)`              |

    FAQ：
      Q: done 和 pending 的界限是如何划分的？
      A: 取决于 return_when 和是否有超时：
         - ALL_COMPLETED 无超时：done=全部，pending=空
         - ALL_COMPLETED 有超时：done=已完成的，pending=超时未完成的
         - FIRST_COMPLETED：done=至少1个（可能多个同时完成），pending=其余
         - FIRST_EXCEPTION：done=异常Task + 异常前已完成的，pending=异常时未完成的
         注意：FIRST_COMPLETED/FIRST_EXCEPTION 不保证 done 中恰好只有1个！

      Q: 异常处理在遍历两个集合时如何进行？遍历逻辑有何区别？
      A: wait() 不会自动传播异常，必须手动遍历 done 集合检查：
         - done 集合：用 t.exception() 检查（返回 None 或异常对象），
           或用 t.result() 获取结果（异常完成时会抛出）
         - pending 集合：通常不需要检查异常（Task 尚未完成），
           调用 result()/exception() 会抛 InvalidStateError
         - pending 的标准处理：t.cancel() 取消，或保存起来稍后重试

      Q: done 和 pending 中可安全调用的方法？
      A: 总结如下：
         ┌────────────────────┬──────────────────────┬─────────────────────────┐
         │      方法           │  done 中的 Task       │  pending 中的 Task       │
         ├────────────────────┼──────────────────────┼─────────────────────────┤
         │  t.result()        │  返回值或抛异常       │  InvalidStateError      │
         │  t.exception()     │  None 或异常对象      │  InvalidStateError      │
         │  t.cancel()        │  返回 False（已完成）  │  返回 True（取消请求发送） │
         │  t.done()          │  True                │  False                  │
         │  t.cancelled()     │  True/False          │  False（尚未取消）        │
         │  t.get_name()      │  安全                │  安全                   │
         └────────────────────┴──────────────────────┴─────────────────────────┘
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

    print("\n\n=== wait_usage ===")

    # 示例1：wait 基本使用 - ALL_COMPLETED
    #   - 无超时时，done=全部Task，pending=空集合
    #   - 遍历 done 用 t.result() 获取结果（此时所有Task都正常完成）
    print("\n--- 示例1：wait ALL_COMPLETED ---")
    tasks = [asyncio.create_task(work(f"W{i}", 0.2 * i)) for i in range(1, 4)]
    done, pending = await asyncio.wait(tasks, return_when=ALL_COMPLETED)
    print(f"  完成: {len(done)} 个, 未完成: {len(pending)} 个")
    for t in done:
        print(f"  -> {t.result()}")

    # 示例2：wait FIRST_COMPLETED - 竞速场景
    #   - done 中至少1个（可能多个同时完成），pending 中是其余未完成的
    #   - pending 中的 Task 需要手动取消，否则它们会继续运行
    #   - 注意：done 不一定恰好只有1个！如果多个Task同时完成，done中会有多个
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
    # 取消剩余任务（pending 中调用 cancel() 是安全的）
    for t in pending:
        t.cancel()
    print("  已取消剩余任务")

    # 示例3：wait FIRST_EXCEPTION - 快速失败
    #   - done 中包含：异常Task + 异常发生前已完成的Task
    #   - pending 中是异常发生时尚未完成的Task
    #   - 遍历 done 时用 t.exception() 区分正常完成和异常完成
    #   - pending 中调用 result()/exception() 会抛 InvalidStateError，只做 cancel()
    print("\n--- 示例3：wait FIRST_EXCEPTION ---")
    tasks3 = [
        asyncio.create_task(work("Normal", 0.5)),
        asyncio.create_task(work_error("Bad", 0.1)),  # 先出错
        asyncio.create_task(work("AlsoNormal", 0.8)),
    ]
    done, pending = await asyncio.wait(tasks3, return_when=FIRST_EXCEPTION)
    print(f"  完成/异常: {len(done)} 个, 剩余: {len(pending)} 个")
    # done 中遍历：用 exception() 区分正常/异常
    for t in done:
        if t.exception():
            print(f"  -> 异常: {t.exception()}")
        else:
            print(f"  -> 结果: {t.result()}")
    # pending 中只做 cancel()，不调用 result()/exception()
    for t in pending:
        t.cancel()

    # 示例4：wait 超时 - pending 不为空的关键场景
    #   - 超时后 done=已完成的，pending=超时未完成的
    #   - 这是 wait() 相比 gather() 的核心优势：可以拿到未完成Task的引用
    #   - pending 中可取消、可重试、可记录日志
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
        

# 注意：进程池中的函数必须是模块级别的（不能是嵌套函数），否则无法 pickle 序列化
def _cpu_intensive_work(n: int):
    """模拟CPU密集型操作（必须模块级，进程池需要 pickle 序列化）"""
    print(f"  [CPU-{n}] 计算开始...")
    total = sum(i * i for i in range(n * 1_000_000))
    print(f"  [CPU-{n}] 计算完成")
    return total

        
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

    FAQ：
      Q: run_in_executor() 的返回值是什么？如何处理？
      A: 返回 asyncio.Future（不是 concurrent.futures.Future），可以直接 await。
         处理方式与普通协程完全一致：
         - 直接 await：result = await loop.run_in_executor(None, func, arg)
         - 配合 gather：results = await asyncio.gather(*[loop.run_in_executor(...)])
         - 配合 wait：done, pending = await asyncio.wait(futures)
         - 配合 as_completed：for f in asyncio.as_completed(futures)
         流程：提交任务 → 立即返回Future → await时协程暂停 → 后台线程执行 → 结果设置到Future → await返回

      Q: 线程池/进程池中的任务如何访问共享变量？是否推荐？
      A: 线程池：可行但需加锁（threading.Lock），同一进程共享内存。
         推荐度 ⚠️ 谨慎：只读配置安全，读写共享尽量用 queue.Queue。
         进程池：不能直接共享（独立内存空间），必须用 multiprocessing.Value/Array/Manager/Queue。
         推荐度 ❌ 不推荐：复杂易错，更好的做法是每个进程独立计算，最后汇总结果。
         最佳实践：
         ┌─────────────────────┬──────────────────────────────────┐
         │  场景               │  推荐做法                         │
         ├─────────────────────┼──────────────────────────────────┤
         │  线程池 + 只读配置   │  ✅ 安全，无需加锁                │
         │  线程池 + 读写共享   │  ⚠️ 必须加锁，尽量用 queue.Queue │
         │  进程池 + 共享状态   │  ❌ 避免，改为独立计算+汇总       │
         │  需要共享复杂状态    │  考虑 asyncio.Queue 在协程间传递  │
         └─────────────────────┴──────────────────────────────────┘

      Q: run_in_executor() 如何处理异常？
      A: 线程/进程中抛出的异常被捕获并设置到返回的 Future 上，await 时重新抛出。
         与 gather 配合：
         - 默认：第一个异常即传播，其他 Future 继续运行（结果丢弃）
         - return_exceptions=True：异常作为结果列表元素返回
         注意事项：
         - CancelledError：await future 时协程被取消，后台任务继续运行（无法取消）
         - 进程池要求：函数必须是模块级的（不能是嵌套函数），参数/返回值/异常必须可 pickle
         - Future 本身不支持 timeout，需配合 asyncio.wait_for
    """
    def blocking_io_work(name: str, delay: float):
        """模拟阻塞IO操作（如 requests.get、同步文件读写）"""
        print(f"  [{name}] 阻塞IO开始 (线程: {threading.current_thread().name})...")
        time.sleep(delay)  # 阻塞 sleep，不是 asyncio.sleep
        print(f"  [{name}] 阻塞IO完成")
        return f"{name}-io-result"

    print("\n\n=== run_in_executor_usage ===")

    loop = asyncio.get_running_loop()

    # 示例1：使用默认线程池执行阻塞IO
    #   - run_in_executor(None, ...) 使用默认线程池，返回 asyncio.Future
    #   - await 该 Future 时，当前协程暂停，事件循环继续处理其他协程
    #   - 后台线程完成后，结果设置到 Future，await 返回拿到结果
    print("\n--- 示例1：默认线程池执行阻塞IO ---")
    result = await loop.run_in_executor(None, blocking_io_work, "IO-Task", 1.0)
    print(f"  结果: {result}")

    # 示例2：并发执行多个阻塞IO任务，配合gather使用
    #   - 多个 run_in_executor 返回的 Future 可以配合 gather 并发执行
    #   - 3个任务在3个不同线程中并发，总耗时 ≈ max(0.5, 0.5, 0.5) = 0.5s
    #   - 如果直接调用 blocking_io_work，总耗时 = 0.5 + 0.5 + 0.5 = 1.5s
    print("\n--- 示例2：并发执行多个阻塞IO ---")
    tasks = [
        loop.run_in_executor(None, blocking_io_work, f"IO-{i}", 0.5)
        for i in range(3)
    ]
    results = await asyncio.gather(*tasks)
    print(f"  所有IO结果: {results}")
    print("  注意：3个阻塞任务在3个线程中并发执行，总耗时约0.5s而非1.5s")

    # 示例3：使用自定义线程池
    #   - 通过 ThreadPoolExecutor(max_workers=2) 限制并发线程数
    #   - 4个任务只有2个线程，分两批执行，总耗时 ≈ 0.3 + 0.3 = 0.6s
    #   - 使用 with 语句确保线程池正确关闭
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
    #   - 进程池适合 CPU 密集型，每个进程有独立 GIL，真正并行计算
    #   - ⚠️ 进程池要求：函数必须是模块级别的，不能是嵌套/局部函数，否则无法 pickle！
    #   - _cpu_intensive_work 已定义为模块级函数（见文件顶部附近）
    #   - 函数参数和返回值也必须可 pickle（int/str/list 等基本类型安全）
    print("\n--- 示例4：进程池执行CPU密集型 ---")
    with ProcessPoolExecutor(max_workers=2) as proc_pool:
        tasks3 = [
            loop.run_in_executor(proc_pool, _cpu_intensive_work, n)
            for n in [5, 8, 3]
        ]
        results3 = await asyncio.gather(*tasks3)
        print(f"  CPU计算结果: {[r for r in results3]}")

    # 示例5：asyncio.to_thread() 便捷方法 (Python 3.9+)
    #   - to_thread() 内部就是调用 run_in_executor(None, ...)
    #   - 语法更简洁，不需要手动获取 event loop
    print("\n--- 示例5：asyncio.to_thread() ---")
    result = await asyncio.to_thread(blocking_io_work, "ToThread", 0.5)
    print(f"  to_thread 结果: {result}")
    print("  注意：asyncio.to_thread() 内部就是调用 run_in_executor(None, ...)")

    # 示例6：对比 - 如果在协程中直接调用阻塞函数会怎样
    #   - 直接调用 time.sleep 会阻塞整个事件循环线程
    #   - 两个 0.3s 的调用串行执行，总耗时 0.6s，且期间所有其他协程都被阻塞
    #   - 正确做法：使用 run_in_executor 或 asyncio.to_thread
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
