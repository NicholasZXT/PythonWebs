"""
研究AnyIO使用。
以 anyio v1.14.0+ 版本为例。
"""
import sys
import os
import subprocess
from typing import TYPE_CHECKING
import asyncio
import anyio
from anyio import run, sleep, create_task_group, TaskHandle, CapacityLimiter
from anyio.abc import TaskGroup, TaskStatus


async def structured_concurrency_basic_usage():
    """
    AnyIO 结构化并发基本使用。

    基本说明：
      - AnyIO 的 TaskGroup（任务组）是结构化并发的核心，通过 async with 创建。
      - TaskGroup 保证：退出 async with 块时，所有子任务都已完成（正常/异常/取消）。
      - 这与 asyncio.create_task() 的根本区别：asyncio 的 Task 生命周期与创建它的协程作用域解耦，
        容易产生"孤儿"Task（忘记 await、异常被静默吞掉、取消父Task子Task继续运行等）。
      - TaskGroup 强制生命周期绑定：子任务的生命周期 ≤ TaskGroup 的作用域。

    TaskGroup 核心 API：
      - tg.start_soon(func, *args, name=None)：启动一个子任务（fire and forget），不等待其就绪。
      - tg.start(func, *args, name=None)：启动一个子任务，等待其通过 task_status.started() 发出就绪信号。
        返回值为子任务传给 task_status.started() 的值。
      - tg.cancel_scope：TaskGroup 关联的 CancelScope，可用于设置超时、屏蔽取消等。

    注意事项：
      - TaskGroup 中的任一子任务抛出异常，会触发取消所有其他子任务（与 asyncio.gather() 完全不同）。
      - start() 要求子任务函数签名包含 task_status: TaskStatus 参数，且子任务中必须调用 task_status.started()。
      - 如果子任务在调用 task_status.started() 之前就抛出异常，start() 会收到该异常。
      - TaskGroup 可以嵌套，内层 TaskGroup 的异常会传播到外层。

    FAQ：
      Q: TaskGroup 与 asyncio.gather() 的核心区别？
      A: 总结如下：
         ┌──────────────────────┬─────────────────────────────────┬──────────────────────────────┐
         │       特性            │  asyncio.gather()               │  anyio.TaskGroup             │
         ├──────────────────────┼─────────────────────────────────┼──────────────────────────────┤
         │  生命周期             │  与创建者作用域解耦             │  严格绑定于 async with 块     │
         │  异常行为             │  首个异常传播，其他继续运行     │  任一异常 → 取消所有其他任务   │
         │  取消传播             │  取消 gather 不取消子 Task      │  取消 TaskGroup → 取消所有子任务│
         │  忘记 await           │  异常被静默吞掉（仅 GC 警告）   │  不可能忘记，作用域强制等待    │
         │  组合封装             │  困难，需手动管理子 Task 列表   │  天然支持嵌套和组合            │
         └──────────────────────┴─────────────────────────────────┴──────────────────────────────┘

      Q: start_soon() vs start() 的使用场景？
      A: start_soon()：不需要等待子任务就绪，适合"发射后不管"的独立任务。
         start()：需要确认子任务已就绪（如服务器已开始监听），适合有依赖关系的任务。
         子任务通过 task_status.started(value) 发送就绪信号，value 会成为 start() 的返回值。

      Q: TaskGroup 的 cancel_scope 有什么用？
      A: cancel_scope 是 AnyIO 中控制取消的核心对象：
         - cancel_scope.cancel()：取消该作用域内的所有任务
         - cancel_scope.deadline：设置绝对截止时间
         - cancel_scope.shield：保护作用域内的任务不被外部取消
         每个 TaskGroup 自动关联一个 cancel_scope，也可手动创建独立的 CancelScope。
    """
    print("=== structured_concurrency_basic_usage ===")

    # 辅助函数：模拟异步任务
    async def do_work(name: str, delay: float):
        print(f"  [{name}] 开始工作，预计 {delay}s...")
        await anyio.sleep(delay)
        print(f"  [{name}] 工作完成")
        return f"{name}-result"

    # 辅助函数：使用 TaskStatus 的就绪通知模式
    async def do_work_with_status(name: str, delay: float, task_status: TaskStatus):
        """
        函数参数中必须要有 task_status: TaskStatus 参数；
        函数体中必须要调用 task_status.started()，通知调用方"我已就绪"。
        """
        print(f"  [{name}] 初始化中...")
        await anyio.sleep(delay * 0.3)  # 模拟初始化
        # 通知调用方：我已就绪，并传递初始状态
        task_status.started(f"{name}-ready")
        # 就绪后继续执行实际工作
        print(f"  [{name}] 已就绪，开始实际工作...")
        await anyio.sleep(delay)
        print(f"  [{name}] 实际工作完成")
        return f"{name}-done"

    # 示例1：TaskGroup 基本使用 - start_soon()
    #   - async with create_task_group() as tg 创建任务组
    #   - tg.start_soon() 启动子任务，不等待就绪
    #   - 退出 async with 块时自动等待所有子任务完成
    #   - 结果顺序与启动顺序无关，各任务并发执行
    print("\n--- 示例1：TaskGroup + start_soon 基本使用 ---")
    async with anyio.create_task_group() as tg:
        # 此 with 块是异步阻塞的，因为 TaskGroup 的 __aexit__() 方法中会执行 await 操作。
        tg.start_soon(do_work, "Task-A", 0.5)
        tg.start_soon(do_work, "Task-B", 0.2)
        tg.start_soon(do_work, "Task-C", 0.3)
        print("  所有任务已启动，等待完成...")
    print("  TaskGroup 块结束，所有子任务已确保完成")

    # 示例2：TaskGroup + start() - 等待子任务就绪
    #   - tg.start() 会阻塞直到子任务调用 task_status.started()
    #   - 返回值是子任务传给 started() 的值
    #   - 适合有依赖关系的场景：确认服务已启动后再做其他操作
    print("\n--- 示例2：TaskGroup + start 等待就绪 ---")
    async with anyio.create_task_group() as tg:
        # start() 等待 Server 就绪后才返回
        ready_msg = await tg.start(do_work_with_status, "Server", 1.0)
        print(f"  收到就绪信号: {ready_msg}")
        # 确认 Server 就绪后，再启动依赖它的 Worker
        tg.start_soon(do_work, "Worker", 0.3)
        print("  Worker 已启动（Server 已就绪）")
    print("  所有任务完成")

    # 示例3：TaskGroup 嵌套 - 内层 TaskGroup 生命周期 ≤ 外层
    #   - 内层 TaskGroup 退出时，其子任务必须全部完成
    #   - 外层 TaskGroup 退出时，内层 TaskGroup 必须已完成
    #   - 这保证了严格的生命周期层级
    print("\n--- 示例3：TaskGroup 嵌套 ---")
    async with anyio.create_task_group() as outer_tg:
        async def inner_group_work():
            print("  内层 TaskGroup 开始...")
            async with anyio.create_task_group() as inner_tg:
                inner_tg.start_soon(do_work, "Inner-A", 0.3)
                inner_tg.start_soon(do_work, "Inner-B", 0.2)
            print("  内层 TaskGroup 结束（所有内层任务已完成）")

        outer_tg.start_soon(inner_group_work)
        outer_tg.start_soon(do_work, "Outer-A", 0.4)
        print("  外层任务已启动...")
    print("  外层 TaskGroup 结束")

    # 示例4：cancel_scope 基本使用 - 超时控制
    #   - tg.cancel_scope.deadline 设置绝对截止时间
    #   - 超时后 TaskGroup 内所有任务被取消
    #   - 也可用 anyio.move_on_after() / anyio.fail_after() 创建独立 CancelScope
    print("\n--- 示例4：cancel_scope 超时控制 ---")
    try:
        async with anyio.create_task_group() as tg:
            # 设置 1 秒后超时
            tg.cancel_scope.deadline = anyio.current_time() + 1.0
            tg.start_soon(do_work, "ShortTask", 0.3)
            tg.start_soon(do_work, "LongTask", 3.0)  # 这个会被取消
            print("  任务已启动，1秒后将超时...")
    except TimeoutError:
        print("  TaskGroup 因超时被取消！")
    print("  超时示例结束")

    # 示例5：对比 asyncio 的"孤儿Task"问题 - AnyIO 如何避免
    #   - asyncio: create_task() 后忘记 await，异常被静默吞掉
    #   - AnyIO: TaskGroup 强制在退出时等待所有子任务，不可能"忘记"
    print("\n--- 示例5：AnyIO 如何避免孤儿Task ---")
    async def work_may_fail(name: str):
        await anyio.sleep(0.2)
        if "Bad" in name:
            raise RuntimeError(f"{name} 失败了！")
        print(f"  [{name}] 正常完成")
        return f"{name}-ok"

    try:
        async with anyio.create_task_group() as tg:
            tg.start_soon(work_may_fail, "GoodTask")
            tg.start_soon(work_may_fail, "BadTask")  # 这个会失败
            tg.start_soon(work_may_fail, "AlsoGoodTask")
    except Exception as e:
        print(f"  捕获异常: {type(e).__name__}: {e}")
        print("  注意：BadTask 失败后，GoodTask 和 AlsoGoodTask 都被自动取消")
        print("  不会出现 asyncio.gather() 中'其他任务继续运行但结果丢弃'的问题")


async def structured_concurrency_exception_usage():
    """
    AnyIO 结构化并发的异常处理。

    基本说明：
      - TaskGroup 的异常处理语义是"一个失败，全部取消"（fail-fast）。
      - 任一子任务抛出异常 → TaskGroup 取消所有其他子任务 → 等待所有子任务终止 → 抛出异常。
      - 这与 asyncio.gather() 完全不同：gather() 默认传播首个异常但其他任务继续运行（结果丢弃）。

    异常传播机制：
      - 子任务抛出异常后，TaskGroup 的 cancel_scope 被取消，触发所有其他子任务的取消。
      - 如果多个子任务同时抛出异常，TaskGroup 会抛出 ExceptionGroup（Python 3.11+）
        或单个异常（Python < 3.11 时抛出第一个，其余被丢弃）。
      - 使用 except* 语法（Python 3.11+）可以分别处理 ExceptionGroup 中的各类异常。

    注意事项：
      - TaskGroup 保证：即使发生异常，所有子任务都会被等待（通过取消机制），不会产生孤儿任务。
      - 如果子任务在 except CancelledError 中吞掉取消信号（不重新抛出），TaskGroup 会一直等待它。
      - 在 Python 3.11+ 中，多个并发异常会被包装为 ExceptionGroup。
      - 使用 anyio.move_on_after() 可以创建"不抛异常的取消"，用于可选操作。

    FAQ：
      Q: TaskGroup 异常处理 vs asyncio.gather() 异常处理？
      A: 总结如下：
         ┌──────────────────────┬─────────────────────────────────┬──────────────────────────────┐
         │       场景            │  asyncio.gather()               │  anyio.TaskGroup             │
         ├──────────────────────┼─────────────────────────────────┼──────────────────────────────┤
         │  单个子任务异常       │  异常传播，其他继续运行(结果丢弃)│  取消所有其他，等待后抛异常    │
         │  多个子任务同时异常   │  第一个异常传播，其余丢弃       │  ExceptionGroup 包装所有异常  │
         │  异常后子任务状态     │  继续运行（孤儿任务）            │  被取消（CancelledError）     │
         │  资源清理保证         │  不保证（孤儿任务可能还在写库）  │  保证（所有子任务被等待终止）  │
         └──────────────────────┴─────────────────────────────────┴──────────────────────────────┘

      Q: 如何在 TaskGroup 中容忍某些子任务失败？
      A: 在子任务内部用 try/except 捕获异常，不让它传播到 TaskGroup 层面。
         或者使用 anyio.create_task_group() 嵌套：内层 TaskGroup 的异常不会直接影响外层。

      Q: ExceptionGroup 如何分别处理不同类型的异常？
      A: Python 3.11+ 使用 except* 语法：
         try:
             ...
         except* ValueError as eg:
             print(f"ValueError: {eg.exceptions}")
         except* RuntimeError as eg:
             print(f"RuntimeError: {eg.exceptions}")
    """
    print("\n\n=== structured_concurrency_exception_usage ===")

    # 辅助函数
    async def work_ok(name: str, delay: float):
        await anyio.sleep(delay)
        print(f"  [{name}] 正常完成")
        return f"{name}-ok"

    async def work_fail(name: str, delay: float, exc_type=RuntimeError):
        await anyio.sleep(delay)
        print(f"  [{name}] 即将抛出异常...")
        raise exc_type(f"{name} 失败了！")

    async def work_with_cleanup(name: str, delay: float):
        """带清理逻辑的任务，展示取消时的资源清理"""
        try:
            print(f"  [{name}] 开始工作...")
            await anyio.sleep(delay)
            print(f"  [{name}] 工作完成")
            return f"{name}-done"
        except Exception as e:
            print(f"  [{name}] 被取消/异常，执行清理... (原因: {type(e).__name__})")
            await anyio.sleep(0.1)  # 模拟清理
            print(f"  [{name}] 清理完成")
            raise  # 必须重新抛出

    # 示例1：单个子任务异常 → 取消所有其他子任务
    #   - BadTask 在 0.2s 后抛出异常
    #   - TaskGroup 立即取消 GoodTask 和 AlsoGood
    #   - 等待所有子任务终止后，异常传播到 async with 块外
    #   - 对比 asyncio.gather()：GoodTask 和 AlsoGood 会继续运行（孤儿任务）
    print("\n--- 示例1：单个异常 → 全部取消 ---")
    try:
        async with anyio.create_task_group() as tg:
            tg.start_soon(work_with_cleanup, "GoodTask", 1.0)
            tg.start_soon(work_fail, "BadTask", 0.2)
            tg.start_soon(work_with_cleanup, "AlsoGood", 1.0)
    except Exception as e:
        print(f"  捕获异常: {type(e).__name__}: {e}")
        print("  注意：GoodTask 和 AlsoGood 都被取消并执行了清理")
        print("  对比 asyncio.gather()：它们会继续运行成为孤儿任务")

    # 示例2：多个子任务同时异常 → ExceptionGroup
    #   - 两个任务几乎同时失败
    #   - Python 3.11+ 抛出 ExceptionGroup 包含所有异常
    #   - Python < 3.11 抛出第一个异常，其余被丢弃
    print("\n--- 示例2：多个同时异常 → ExceptionGroup ---")
    try:
        async with anyio.create_task_group() as tg:
            tg.start_soon(work_fail, "Fail-A", 0.1)
            tg.start_soon(work_fail, "Fail-B", 0.1)
    except BaseException as e:
        print(f"  捕获异常类型: {type(e).__name__}")
        # BaseExceptionGroup 仅在 Python 3.11+ 可用
        if hasattr(e, 'exceptions'):
            print(f"  ExceptionGroup 包含 {len(e.exceptions)} 个异常:")
            for i, exc in enumerate(e.exceptions):
                print(f"    [{i}] {type(exc).__name__}: {exc}")
        else:
            print(f"  单个异常: {e}")
            print("  (Python < 3.11 只抛出第一个异常)")

    # 示例3：在子任务内部容忍异常（不让它传播到 TaskGroup）
    #   - 子任务内部 try/except 捕获异常，TaskGroup 层面不受影响
    #   - 这是"容忍部分失败"的正确做法
    print("\n--- 示例3：子任务内部容忍异常 ---")
    async def work_tolerant(name: str, delay: float, should_fail: bool):
        try:
            await anyio.sleep(delay)
            if should_fail:
                raise ValueError(f"{name} 内部错误")
            print(f"  [{name}] 正常完成")
            return f"{name}-ok"
        except ValueError as e:
            print(f"  [{name}] 内部捕获异常: {e}，返回 fallback")
            return f"{name}-fallback"

    async with anyio.create_task_group() as tg:
        tg.start_soon(work_tolerant, "T1", 0.2, False)
        tg.start_soon(work_tolerant, "T2", 0.1, True)  # 内部处理
        tg.start_soon(work_tolerant, "T3", 0.3, False)
    print("  所有任务完成（T2 的异常被内部处理，不影响其他）")

    # 示例4：嵌套 TaskGroup 隔离异常
    #   - 内层 TaskGroup 的异常不会直接传播到外层
    #   - 外层可以捕获内层的异常并决定如何处理
    print("\n--- 示例4：嵌套 TaskGroup 隔离异常 ---")
    async def inner_group_with_failure():
        """内层 TaskGroup，内部有任务失败"""
        try:
            async with anyio.create_task_group() as inner_tg:
                inner_tg.start_soon(work_ok, "Inner-OK", 0.2)
                inner_tg.start_soon(work_fail, "Inner-Fail", 0.1)
        except Exception as e:
            print(f"  内层 TaskGroup 捕获: {type(e).__name__}: {e}")
            # 内层处理了异常，外层不受影响
            return "inner-handled"

    async with anyio.create_task_group() as outer_tg:
        outer_tg.start_soon(inner_group_with_failure)
        outer_tg.start_soon(work_ok, "Outer-OK", 0.3)
    print("  外层 TaskGroup 正常完成（内层异常被隔离）")

    # 示例5：move_on_after - 不抛异常的取消
    #   - anyio.move_on_after(delay) 创建 CancelScope，超时后取消但不抛异常
    #   - 与 fail_after(delay) 的区别：fail_after 超时后抛出 TimeoutError
    #   - 适合"可选操作"：超时就算了，继续执行后续逻辑
    print("\n--- 示例5：move_on_after 不抛异常的取消 ---")
    with anyio.move_on_after(0.5) as scope:
        print("  move_on_after: 开始一个最多0.5s的操作...")
        await anyio.sleep(2.0)  # 这个会被取消
        print("  （不会执行到这里）")
    if scope.cancel_called:
        print("  操作被取消（move_on_after 超时），但不抛异常，继续执行")
    print("  move_on_after 块之后的代码正常执行")

    # 对比：fail_after 超时抛异常
    print("\n  对比 fail_after：")
    try:
        with anyio.fail_after(0.3):
            await anyio.sleep(2.0)
    except TimeoutError:
        print("  fail_after 超时，抛出 TimeoutError")



async def structured_concurrency_cancellation_usage():
    """
    AnyIO 结构化并发的取消传播处理。

    基本说明：
      - AnyIO 的取消机制基于 CancelScope（取消作用域），每个 TaskGroup 自动关联一个。
      - 取消是协作式的：被取消的任务在下一个 await 点抛出 CancelledError。
      - 取消传播是可靠的：取消父 CancelScope → 所有子 CancelScope 被取消 → 所有子任务被取消。
      - 这与 asyncio 的关键区别：asyncio 中取消父 Task 不会自动取消子 Task。

    CancelScope 核心 API：
      - cancel()：取消该作用域内的所有任务。
      - deadline：设置绝对截止时间（基于 anyio.current_time()）。
      - shield：设为 True 可保护作用域内的任务不被外部取消。
      - cancel_called：只读属性，表示取消是否已被触发。

    注意事项：
      - 被取消的任务必须在 except CancelledError 中重新 raise，否则 CancelScope 会一直等待。
      - shield=True 只保护"从外部进入"的取消，内部任务自己抛出的 CancelledError 不受保护。
      - 取消传播是自顶向下的：父 CancelScope 取消 → 子 CancelScope 取消 → 孙 CancelScope 取消。
      - anyio.move_on_after() 和 anyio.fail_after() 本质上是创建了带 deadline 的 CancelScope。

    FAQ：
      Q: AnyIO 取消 vs asyncio 取消的核心区别？
      A: 总结如下：
         ┌──────────────────────┬─────────────────────────────────┬──────────────────────────────┐
         │       场景            │  asyncio                       │  anyio                       │
         ├──────────────────────┼─────────────────────────────────┼──────────────────────────────┤
         │  取消父Task           │  子Task 不受影响（孤儿）        │  子任务自动被取消             │
         │  取消传播             │  手动管理，容易遗漏             │  自动传播，CancelScope 层级   │
         │  超时取消             │  wait_for() 取消内部协程        │  fail_after/move_on_after    │
         │  屏蔽取消             │  asyncio.shield()              │  cancel_scope.shield = True  │
         │  取消后资源清理       │  依赖 except CancelledError     │  同样依赖，但保证所有任务被等待│
         └──────────────────────┴─────────────────────────────────┴──────────────────────────────┘

      Q: shield 的使用场景？
      A: 保护关键操作不被取消，例如：
         - 数据库事务提交（一旦开始就不能中断）
         - 文件写入的 flush 操作
         - 发送"操作已取消"的通知
         注意：shield 只保护被包裹的代码，如果内部又创建了子任务，子任务不受 shield 保护。

      Q: move_on_after vs fail_after 的区别？
      A: move_on_after：超时后取消但不抛异常，通过 scope.cancel_called 判断是否超时。
         fail_after：超时后取消并抛出 TimeoutError。
         选择：可选操作用 move_on_after，必须完成的操作用 fail_after。
    """
    print("\n\n=== structured_concurrency_cancellation_usage ===")

    # 辅助函数
    async def do_work(name: str, delay: float):
        try:
            print(f"  [{name}] 开始工作，预计 {delay}s...")
            await anyio.sleep(delay)
            print(f"  [{name}] 工作完成")
            return f"{name}-result"
        except Exception as e:
            print(f"  [{name}] 被取消/异常: {type(e).__name__}，执行清理...")
            await anyio.sleep(0.05)
            print(f"  [{name}] 清理完成")
            raise

    async def critical_work(name: str, delay: float):
        """模拟关键操作（如数据库写入），不应被取消"""
        print(f"  [{name}] 关键操作开始...")
        await anyio.sleep(delay)
        print(f"  [{name}] 关键操作完成")
        return f"{name}-success"

    # 示例1：取消传播 - 父 CancelScope 取消 → 子任务全部取消
    #   - 手动调用 cancel_scope.cancel() 取消整个 TaskGroup
    #   - 所有子任务收到 CancelledError，执行清理后终止
    #   - 对比 asyncio：取消父 Task 不会自动取消子 Task
    print("\n--- 示例1：取消传播 - 父取消 → 子全部取消 ---")
    async with anyio.create_task_group() as tg:
        tg.start_soon(do_work, "Child-A", 3.0)
        tg.start_soon(do_work, "Child-B", 3.0)
        tg.start_soon(do_work, "Child-C", 3.0)
        await anyio.sleep(0.3)  # 让子任务先启动
        print("  手动取消 TaskGroup...")
        tg.cancel_scope.cancel()
    print("  TaskGroup 退出，所有子任务已被取消并清理")

    # 示例2：嵌套 CancelScope 的取消传播
    #   - 外层 CancelScope 取消 → 内层 CancelScope 自动取消
    #   - 这是 AnyIO 的核心保证：取消传播是自顶向下的
    print("\n--- 示例2：嵌套 CancelScope 取消传播 ---")
    async def nested_work():
        async with anyio.create_task_group() as inner_tg:
            inner_tg.start_soon(do_work, "Inner-Deep", 5.0)
            await anyio.sleep(10)  # 长时间等待

    async with anyio.create_task_group() as outer_tg:
        outer_tg.start_soon(nested_work)
        await anyio.sleep(0.3)
        print("  取消外层 TaskGroup...")
        outer_tg.cancel_scope.cancel()
    print("  外层退出，内层 Inner-Deep 也被自动取消")

    # 示例3：shield 保护关键操作不被取消
    #   - shield=True 保护作用域内的代码不受外部取消影响
    #   - 适合保护数据库事务提交等不可中断的操作
    print("\n--- 示例3：shield 保护关键操作 ---")
    async with anyio.create_task_group() as tg:
        async def shielded_work():
            print("  开始：先做普通操作...")
            await anyio.sleep(0.2)
            # 关键操作：使用 shield 保护
            print("  进入关键操作（shield 保护中）...")
            with anyio.CancelScope(shield=True):
                await critical_work("DB-Commit", 0.5)
            print("  关键操作完成，退出 shield")

        tg.start_soon(shielded_work)
        await anyio.sleep(0.3)
        print("  外部取消 TaskGroup...")
        tg.cancel_scope.cancel()
    print("  TaskGroup 退出（关键操作在 shield 保护下完成）")

    # 示例4：move_on_after - 超时取消但不抛异常
    #   - 适合"可选操作"：超时就算了，继续执行
    #   - scope.cancel_called 判断是否被取消
    print("\n--- 示例4：move_on_after 可选超时 ---")
    with anyio.move_on_after(0.5) as scope:
        print("  开始可选操作（最多 0.5s）...")
        await anyio.sleep(2.0)  # 太慢，会被取消
        print("  （不会执行到这里）")
    if scope.cancel_called:
        print("  可选操作超时被取消，继续执行后续逻辑")
    else:
        print("  可选操作在超时前完成")

    # 示例5：fail_after - 超时取消并抛异常
    #   - 适合"必须完成"的操作：超时就是错误
    print("\n--- 示例5：fail_after 超时抛异常 ---")
    try:
        with anyio.fail_after(0.5):
            print("  开始必须完成的操作（最多 0.5s）...")
            await anyio.sleep(2.0)
    except TimeoutError:
        print("  操作超时！TimeoutError 被抛出")

    # 示例6：对比 asyncio - 取消父Task子Task变孤儿
    #   - 这是 asyncio 的经典坑点，AnyIO 通过 CancelScope 层级自动解决
    print("\n--- 示例6：AnyIO 如何避免 asyncio 的孤儿Task问题 ---")
    async def parent_with_children():
        """AnyIO 版本：父被取消时子自动取消"""
        async with anyio.create_task_group() as tg:
            tg.start_soon(do_work, "Child-1", 5.0)
            tg.start_soon(do_work, "Child-2", 5.0)
            print("  父任务: 子任务已创建，等待中...")
            await anyio.sleep(10)  # 长时间等待

    async with anyio.create_task_group() as tg:
        tg.start_soon(parent_with_children)
        await anyio.sleep(0.3)
        print("  取消父任务...")
        tg.cancel_scope.cancel()
    print("  父任务退出，Child-1 和 Child-2 也被自动取消")
    print("  对比 asyncio：需要手动遍历子Task列表逐个cancel()")

    # 示例7：deadline 绝对时间超时
    print("\n--- 示例7：deadline 绝对时间超时 ---")
    deadline = anyio.current_time() + 0.8
    print(f"  设置截止时间: 当前时间 + 0.8s")
    try:
        async with anyio.create_task_group() as tg:
            tg.cancel_scope.deadline = deadline
            tg.start_soon(do_work, "DeadlineTask", 2.0)
    except TimeoutError:
        print("  截止时间到达，任务被取消")



async def structured_concurrency_combination_usage():
    """
    AnyIO 结构化并发的组合封装。

    基本说明：
      - AnyIO 的 TaskGroup 天然支持组合封装：将并发逻辑封装为可复用的 async 函数。
      - 每个被封装的函数内部使用自己的 TaskGroup，调用方无需关心内部并发细节。
      - 这与 asyncio 的关键区别：asyncio 中封装并发逻辑需要手动管理子 Task 列表，
        且异常/取消传播需要自行实现，容易出错。

    组合封装的核心模式：
      - 模式1：封装并发操作 - 函数内部使用 TaskGroup，对外表现为普通协程。
      - 模式2：使用 TaskStatus 传递就绪信号 - 封装"需要就绪通知"的并发服务。
      - 模式3：嵌套 TaskGroup - 外层编排多个封装的并发操作。
      - 模式4：带超时的封装 - 使用 fail_after/move_on_after 包装。

    注意事项：
      - 封装的函数内部异常会正确传播到调用方（通过 TaskGroup 的异常机制）。
      - 调用方取消时，封装函数内部的所有子任务都会被自动取消（CancelScope 层级传播）。
      - 不要在封装函数外部持有内部 TaskGroup 的引用，这会破坏结构化并发的保证。
      - 使用 TaskStatus 时，确保所有代码路径都调用了 task_status.started()。

    FAQ：
      Q: 为什么 AnyIO 的 TaskGroup 比 asyncio 更容易组合封装？
      A: asyncio 中封装并发操作需要：
         1. 手动维护子 Task 列表
         2. 手动实现"一个失败全部取消"的逻辑
         3. 手动处理取消传播（父取消 → 子取消）
         4. 手动确保异常时所有子 Task 被等待
         AnyIO 的 TaskGroup 自动处理以上所有问题，封装函数只需关注业务逻辑。

      Q: 封装函数中可以使用 return 返回值吗？
      A: 可以。TaskGroup 退出后，封装函数可以正常 return 返回值。
         但注意：TaskGroup 内部子任务的返回值不会自动收集，需要自行处理
         （如通过共享变量、队列等方式收集结果）。

      Q: 如何在封装函数中收集子任务的结果？
      A: 常用方式：
         - 使用列表 + 回调：在子任务中将结果 append 到外部列表
         - 使用 anyio.create_memory_object_stream()：子任务通过 stream 发送结果
         - 使用 anyio.Lock 保护的共享变量
    """
    print("\n\n=== structured_concurrency_combination_usage ===")

    # 辅助函数
    async def fetch_api(name: str, delay: float):
        """模拟调用远程 API"""
        print(f"    [API:{name}] 请求中...")
        await anyio.sleep(delay)
        print(f"    [API:{name}] 返回结果")
        return {name: f"data-from-{name}"}

    async def fetch_api_may_fail(name: str, delay: float, should_fail: bool = False):
        """模拟可能失败的 API 调用"""
        await anyio.sleep(delay)
        if should_fail:
            raise RuntimeError(f"API:{name} 调用失败")
        print(f"    [API:{name}] 返回结果")
        return {name: f"data-from-{name}"}

    # 模式1：封装并发操作 - 对外表现为普通协程
    #   - 函数内部使用 TaskGroup 并发调用多个 API
    #   - 调用方只需 await 这个函数，无需关心内部并发细节
    #   - 结果通过共享列表收集
    print("\n--- 模式1：封装并发操作为普通协程 ---")
    async def fetch_all_users():
        """封装：并发获取多个用户数据源，对外表现为一个协程"""
        results = []

        async def fetch_and_store(name: str, delay: float):
            data = await fetch_api(name, delay)
            results.append(data)

        async with anyio.create_task_group() as tg:
            tg.start_soon(fetch_and_store, "UserDB", 0.3)
            tg.start_soon(fetch_and_store, "UserCache", 0.1)
            tg.start_soon(fetch_and_store, "UserProfile", 0.2)
        # TaskGroup 退出时所有子任务已完成
        return results

    # 调用方：就像调用普通协程一样
    user_data = await fetch_all_users()
    print(f"  获取到的用户数据: {user_data}")
    print("  注意：调用方无需知道内部是并发还是串行")

    # 模式2：使用 TaskStatus 封装需要就绪通知的服务
    #   - 模拟一个"微服务启动器"：启动多个子服务，全部就绪后才返回
    print("\n--- 模式2：TaskStatus 封装就绪通知 ---")
    async def start_microservice(name: str, delay: float, task_status: TaskStatus):
        """模拟启动一个微服务"""
        print(f"    [{name}] 正在启动...")
        await anyio.sleep(delay)  # 模拟启动过程
        print(f"    [{name}] 已就绪")
        task_status.started(f"{name}:8000")  # 通知就绪，传递端口号
        # 就绪后继续运行（模拟服务运行中）
        try:
            await anyio.sleep(100)  # 长时间运行
        except Exception:
            print(f"    [{name}] 正在关闭...")
            await anyio.sleep(0.1)
            print(f"    [{name}] 已关闭")
            raise

    async def launch_all_services():
        """封装：启动所有微服务，全部就绪后返回地址列表"""
        addresses = {}

        async def start_and_record(name: str, delay: float):
            async with anyio.create_task_group() as tg:
                addr = await tg.start(start_microservice, name, delay)
                addresses[name] = addr

        async with anyio.create_task_group() as tg:
            tg.start_soon(start_and_record, "AuthService", 0.3)
            tg.start_soon(start_and_record, "DataService", 0.2)
            tg.start_soon(start_and_record, "GatewayService", 0.4)
        return addresses

    async with anyio.create_task_group() as tg:
        tg.start_soon(launch_all_services)
        await anyio.sleep(1.0)  # 等待服务全部启动
        tg.cancel_scope.cancel()  # 演示后关闭
    print("  所有服务已关闭")

    # 模式3：嵌套 TaskGroup 编排多个封装操作
    #   - 外层 TaskGroup 编排多个封装好的并发操作
    #   - 每个封装操作内部又有自己的 TaskGroup
    #   - 异常和取消正确传播到每一层
    print("\n--- 模式3：嵌套编排多个封装操作 ---")
    async def fetch_user_data():
        """封装：获取用户相关数据"""
        results = []
        async def collect(name, delay):
            data = await fetch_api(name, delay)
            results.append(data)
        async with anyio.create_task_group() as tg:
            tg.start_soon(collect, "UserInfo", 0.2)
            tg.start_soon(collect, "UserOrders", 0.3)
        return {"user": results}

    async def fetch_product_data():
        """封装：获取产品相关数据"""
        results = []
        async def collect(name, delay):
            data = await fetch_api(name, delay)
            results.append(data)
        async with anyio.create_task_group() as tg:
            tg.start_soon(collect, "ProductList", 0.15)
            tg.start_soon(collect, "ProductPrice", 0.25)
        return {"product": results}

    # 外层编排：并发执行两个封装好的操作
    all_results = {}
    async def run_and_store(fetcher):
        result = await fetcher()
        all_results.update(result)

    async with anyio.create_task_group() as tg:
        tg.start_soon(run_and_store, fetch_user_data)
        tg.start_soon(run_and_store, fetch_product_data)
    print(f"  编排结果: {all_results}")
    print("  注意：外层编排 + 内层并发，异常和取消自动传播到每一层")

    # 模式4：带超时的封装操作
    #   - 使用 fail_after 为整个封装操作设置超时
    #   - 超时后内部所有子任务被自动取消
    print("\n--- 模式4：带超时的封装操作 ---")
    async def fetch_with_timeout(timeout: float):
        """封装：带超时的并发数据获取"""
        results = []
        async def collect(name, delay):
            data = await fetch_api(name, delay)
            results.append(data)

        try:
            with anyio.fail_after(timeout):
                async with anyio.create_task_group() as tg:
                    tg.start_soon(collect, "FastSource", 0.2)
                    tg.start_soon(collect, "SlowSource", 3.0)  # 太慢
            return results
        except TimeoutError:
            print("    封装操作超时！内部所有请求被取消")
            return results  # 返回已收集的部分结果

    result = await fetch_with_timeout(0.5)
    print(f"  超时封装结果: {result}")

    # 模式5：封装可复用的并发原语 - 竞速模式
    #   - 多个数据源竞速，谁先返回用谁的
    #   - 使用 move_on_after + TaskGroup 实现
    print("\n--- 模式5：封装竞速模式 ---")
    async def race_fetch(sources: list, timeout: float = 2.0):
        """封装：多数据源竞速，返回第一个成功的结果"""
        result_holder = []

        async def try_source(name: str, delay: float):
            try:
                data = await fetch_api(name, delay)
                if not result_holder:  # 只取第一个
                    result_holder.append(data)
                    print(f"    竞速胜出: {name}")
            except Exception:
                pass  # 失败的源被忽略

        with anyio.move_on_after(timeout) as scope:
            async with anyio.create_task_group() as tg:
                for name, delay in sources:
                    tg.start_soon(try_source, name, delay)

        if result_holder:
            return result_holder[0]
        return None

    winner = await race_fetch([
        ("Source-A", 0.5),
        ("Source-B", 0.2),  # 这个最快
        ("Source-C", 0.8),
    ])
    print(f"  竞速结果: {winner}")

    # 模式6：对比 asyncio - 封装并发操作需要手动管理
    #   - 展示 asyncio 中封装同样逻辑的复杂度
    print("\n--- 模式6：对比 asyncio 封装复杂度 ---")
    print("  AnyIO 封装：只需 async with create_task_group() 包裹业务逻辑")
    print("  asyncio 封装：需要手动维护 Task 列表、手动取消、手动异常处理")
    print("  示例：AnyIO 的 fetch_all_users() 只需 ~10 行，asyncio 同等功能需 ~30+ 行")


    
async def synchronization_primitive_usage():
    """
    AnyIO 同步原语使用。

    基本说明：
      - AnyIO 提供与 asyncio 类似的同步原语，但设计更一致、跨后端（asyncio/trio）。
      - 所有同步原语都必须在 async 函数中使用，且是协程安全的（但**非线程安全**）。
      - 核心原语：Lock、Semaphore、Event、Condition、CapacityLimiter。

    各原语用途：
      - Lock：互斥锁，保护共享资源，同一时间只有一个协程能持有。
      - Semaphore：信号量，限制同时访问资源的协程数量。
      - Event：事件，一个协程设置事件，其他协程等待事件发生。
      - Condition：条件变量，协程等待某个条件满足后被通知。
      - CapacityLimiter：容量限制器，类似 Semaphore 但可与 TaskGroup 集成。

    注意事项：
      - Lock/Semaphore 支持 async with 语法，自动获取和释放。
      - 与 asyncio 不同，AnyIO 的同步原语不绑定到特定事件循环，可在不同后端间移植。
      - CapacityLimiter 是 AnyIO 特有的，可限制 TaskGroup 中同时运行的任务数。
      - 不要在同步代码（如 to_thread.run_sync() 的回调）中使用这些原语，它们不是线程安全的。

    FAQ：
      Q: AnyIO 同步原语 vs asyncio 同步原语？
      A: 功能基本对应，但 AnyIO 的优势：
         - 跨后端可移植（asyncio/trio 均可使用）
         - CapacityLimiter 是独有功能，比 Semaphore 更易与 TaskGroup 集成
         - API 更一致，所有原语都支持 async with
         - 不绑定到特定事件循环对象

      Q: CapacityLimiter vs Semaphore 的区别？
      A: CapacityLimiter 专为限制 TaskGroup 并发数设计：
         - 可直接传给 create_task_group() 的 limiter 参数
         - 支持 total_tokens 属性动态调整容量
         - Semaphore 更通用，适合手动 acquire/release 场景
    """
    print("\n\n=== synchronization_primitive_usage ===")

    # 辅助函数
    async def do_work(name: str, delay: float):
        print(f"    [{name}] 开始...")
        await anyio.sleep(delay)
        print(f"    [{name}] 完成")
        return f"{name}-done"

    # 示例1：Lock 互斥锁 - 保护共享资源
    #   - async with lock 自动获取和释放
    #   - 同一时间只有一个协程能进入临界区
    print("\n--- 示例1：Lock 互斥锁 ---")
    lock = anyio.Lock()
    shared_counter = 0

    async def locked_increment(name: str):
        nonlocal shared_counter
        async with lock:
            print(f"  [{name}] 获取锁，当前值: {shared_counter}")
            current = shared_counter
            await anyio.sleep(0.1)  # 模拟处理
            shared_counter = current + 1
            print(f"  [{name}] 释放锁，新值: {shared_counter}")

    async with anyio.create_task_group() as tg:
        for i in range(3):
            tg.start_soon(locked_increment, f"Worker-{i}")
    print(f"  最终值: {shared_counter} (预期: 3)")

    # 示例2：Semaphore 信号量 - 限制并发数
    #   - 同时最多 N 个协程持有信号量
    #   - 适合限制对有限资源的并发访问（如数据库连接池）
    print("\n--- 示例2：Semaphore 信号量 ---")
    semaphore = anyio.Semaphore(2)  # 最多2个并发

    async def limited_work(name: str, delay: float):
        async with semaphore:
            print(f"  [{name}] 获取信号量，开始工作...")
            await anyio.sleep(delay)
            print(f"  [{name}] 释放信号量，工作完成")

    async with anyio.create_task_group() as tg:
        tg.start_soon(limited_work, "S1", 0.5)
        tg.start_soon(limited_work, "S2", 0.5)
        tg.start_soon(limited_work, "S3", 0.3)
        tg.start_soon(limited_work, "S4", 0.3)
    print("  注意：S1/S2 先执行，S3/S4 等待信号量释放后才执行")

    # 示例3：Event 事件 - 协程间通知
    #   - 一个协程 set() 事件，其他协程 wait() 等待
    #   - 适合"等待某个条件就绪"的场景
    print("\n--- 示例3：Event 事件通知 ---")
    event = anyio.Event()

    async def waiter(name: str):
        print(f"  [{name}] 等待事件...")
        await event.wait()
        print(f"  [{name}] 收到事件通知，继续执行")

    async def setter():
        await anyio.sleep(0.5)
        print("  [Setter] 设置事件")
        event.set()

    async with anyio.create_task_group() as tg:
        tg.start_soon(waiter, "Waiter-A")
        tg.start_soon(waiter, "Waiter-B")
        tg.start_soon(setter)
    print("  所有等待者都收到了通知")

    # 示例4：Condition 条件变量 - 等待特定条件
    #   - 比 Event 更灵活，支持 notify() 唤醒指定数量的等待者
    #   - 适合生产者-消费者模式
    print("\n--- 示例4：Condition 条件变量 ---")
    condition = anyio.Condition()
    items = []

    async def producer():
        for i in range(3):
            await anyio.sleep(0.2)
            async with condition:
                items.append(f"item-{i}")
                print(f"  [Producer] 生产: item-{i}")
                condition.notify(1)  # 唤醒一个消费者

    async def consumer(name: str):
        async with condition:
            while not items:
                print(f"  [{name}] 等待商品...")
                await condition.wait()
            item = items.pop(0)
            print(f"  [{name}] 消费: {item}")

    async with anyio.create_task_group() as tg:
        tg.start_soon(producer)
        tg.start_soon(consumer, "Consumer-A")
        tg.start_soon(consumer, "Consumer-B")
        tg.start_soon(consumer, "Consumer-C")
    print("  所有商品已消费")

    # 示例5：CapacityLimiter - 限制 TaskGroup 并发数
    #   - AnyIO 特有功能，通过 tg.capacity_limiter 属性设置
    #   - 比 Semaphore 更简洁：不需要在每个任务中手动 acquire/release
    print("\n--- 示例5：CapacityLimiter 限制 TaskGroup 并发 ---")
    limiter = anyio.CapacityLimiter(2)  # 最多2个任务同时运行

    async with anyio.create_task_group() as tg:
        tg.capacity_limiter = limiter
        for i in range(5):
            tg.start_soon(do_work, f"CL-{i}", 0.3)
    print("  注意：最多2个任务同时运行，其余排队等待")

    # 对比：使用 CapacityLimiter 参数
    print("\n  对比：使用 limiter 参数限制并发 ---")
    limiter2 = anyio.CapacityLimiter(2)
    async with anyio.create_task_group() as tg:
        tg.capacity_limiter = limiter2
        for i in range(4):
            tg.start_soon(do_work, f"Limited-{i}", 0.2)
    print("  同样最多2个并发，但无需在每个任务中手动 acquire")

    # 示例6：动态调整 CapacityLimiter 容量
    print("\n--- 示例6：动态调整容量 ---")
    limiter3 = anyio.CapacityLimiter(1)  # 初始容量1

    async def dynamic_worker(name: str):
        print(f"  [{name}] 开始 (当前容量: {limiter3.total_tokens})")
        await anyio.sleep(0.3)
        print(f"  [{name}] 完成")

    async def adjust_capacity():
        await anyio.sleep(0.1)
        print("  调整容量: 1 -> 3")
        limiter3.total_tokens = 3  # 动态扩容

    async with anyio.create_task_group() as tg:
        tg.start_soon(adjust_capacity)
        async with anyio.create_task_group() as inner_tg:
            inner_tg.capacity_limiter = limiter3
            for i in range(4):
                inner_tg.start_soon(dynamic_worker, f"Dyn-{i}")
    print("  容量动态调整生效")


async def stream_usage():
    """
    AnyIO Stream 封装使用。

    基本说明：
      - AnyIO 提供内存流（MemoryObjectStream）用于协程间的消息传递。
      - 通过 anyio.create_memory_object_stream() 创建一对 send/receive 流。
      - 支持带缓冲的流（buffered）和容量限制（max_buffer_size）。
      - 类似 Go 语言的 channel，是协程间通信的首选方式。

    核心 API：
      - create_memory_object_stream(max_buffer_size=0)：创建一对 (send, receive) 流。
        max_buffer_size=0 表示无缓冲（发送方等待接收方），>0 表示有缓冲。
      - send_stream.send(item)：发送数据，如果缓冲区满则等待。
      - send_stream.send_nowait(item)：发送数据，如果缓冲区满则抛出 WouldBlock。
      - receive_stream.receive()：接收数据，如果无数据则等待。
      - receive_stream.receive_nowait()：接收数据，如果无数据则抛出 WouldBlock。
      - send_stream.close() / receive_stream.close()：关闭流。
      - clone()：克隆 send 或 receive 流，多个协程可共享。

    注意事项：
      - 流是单向的：send_stream 只能发送，receive_stream 只能接收。
      - 关闭 send_stream 后，receive_stream 在消费完所有缓冲数据后会抛出 EndOfStream。
      - 关闭 receive_stream 后，send_stream 的 send() 会抛出 BrokenResourceError。
      - 流不是线程安全的，只能在协程中使用。
      - clone() 创建的副本共享同一个底层缓冲区。

    典型使用场景：
      - 生产者-消费者模式
      - 协程间管道式数据处理
      - 广播消息给多个消费者（clone receive_stream）

    FAQ：
      Q: MemoryObjectStream vs asyncio.Queue？
      A: 总结如下：
         ┌──────────────────────┬─────────────────────────────────┬──────────────────────────────┐
         │       特性            │  asyncio.Queue                  │  anyio.MemoryObjectStream    │
         ├──────────────────────┼─────────────────────────────────┼──────────────────────────────┤
         │  方向                 │  双向（同一对象 put/get）        │  单向（send 和 receive 分离） │
         │  关闭语义             │  无明确关闭机制                  │  close() + EndOfStream       │
         │  广播                 │  不支持                          │  clone() 支持多消费者         │
         │  背压                 │  maxsize 限制                   │  max_buffer_size 限制         │
         │  跨后端               │  仅 asyncio                     │  asyncio/trio 均可            │
         └──────────────────────┴─────────────────────────────────┴──────────────────────────────┘

      Q: 何时使用无缓冲 vs 有缓冲？
      A: 无缓冲（max_buffer_size=0）：发送方必须等待接收方就绪，适合严格同步场景。
         有缓冲（max_buffer_size>0）：发送方可以先发送到缓冲区，适合解耦生产者和消费者速度。
    """
    print("\n\n=== stream_usage ===")

    # 示例1：基本生产者-消费者模式
    #   - create_memory_object_stream() 创建一对流
    #   - 生产者通过 send_stream 发送，消费者通过 receive_stream 接收
    #   - 生产者关闭 send_stream 后，消费者收到 EndOfStream
    print("\n--- 示例1：基本生产者-消费者 ---")
    send_stream, receive_stream = anyio.create_memory_object_stream(max_buffer_size=3)

    async def producer():
        for i in range(5):
            msg = f"msg-{i}"
            print(f"  [Producer] 发送: {msg}")
            await send_stream.send(msg)
            await anyio.sleep(0.1)
        print("  [Producer] 生产完毕，关闭发送流")
        await send_stream.aclose()

    async def consumer():
        try:
            async for msg in receive_stream:  # 异步迭代直到 EndOfStream
                print(f"  [Consumer] 接收: {msg}")
                await anyio.sleep(0.15)  # 模拟处理耗时
        except anyio.EndOfStream:
            print("  [Consumer] 流已关闭（EndOfStream）")

    async with anyio.create_task_group() as tg:
        tg.start_soon(producer)
        tg.start_soon(consumer)
    print("  生产者-消费者完成")

    # 示例2：多生产者-多消费者（clone 实现广播）
    #   - clone() 创建流的副本，多个消费者各自独立接收
    #   - 每个 clone 的流独立消费，互不影响
    print("\n--- 示例2：多消费者广播（clone） ---")
    send_stream2, receive_stream2 = anyio.create_memory_object_stream(max_buffer_size=5)

    async def broadcaster():
        for i in range(3):
            msg = f"broadcast-{i}"
            print(f"  [Broadcaster] 广播: {msg}")
            await send_stream2.send(msg)
            await anyio.sleep(0.2)
        await send_stream2.aclose()

    async def listener(name: str, stream):
        async for msg in stream:
            print(f"  [{name}] 收到: {msg}")

    # clone 创建两个独立的接收流
    listener_a_stream = receive_stream2.clone()
    listener_b_stream = receive_stream2.clone()

    async with anyio.create_task_group() as tg:
        tg.start_soon(broadcaster)
        tg.start_soon(listener, "Listener-A", listener_a_stream)
        tg.start_soon(listener, "Listener-B", listener_b_stream)
    # 关闭原始 receive_stream（clone 的流不受影响，已独立消费）
    await receive_stream2.aclose()
    print("  广播完成，两个监听者都收到了所有消息")

    # 示例3：无缓冲流 - 严格同步
    #   - max_buffer_size=0 表示发送方必须等待接收方
    #   - 适合需要严格同步的场景
    print("\n--- 示例3：无缓冲流（严格同步） ---")
    send_sync, recv_sync = anyio.create_memory_object_stream(max_buffer_size=0)

    async def sync_sender():
        for i in range(3):
            print(f"  [Sender] 准备发送 msg-{i}...")
            await send_sync.send(f"msg-{i}")
            print(f"  [Sender] msg-{i} 已被接收方取走")
        await send_sync.aclose()

    async def sync_receiver():
        await anyio.sleep(0.3)  # 模拟接收方处理慢
        async for msg in recv_sync:
            print(f"  [Receiver] 收到: {msg}")
            await anyio.sleep(0.3)

    async with anyio.create_task_group() as tg:
        tg.start_soon(sync_sender)
        tg.start_soon(sync_receiver)
    print("  注意：发送方每次发送后必须等待接收方取走才能继续")

    # 示例4：管道式数据处理
    #   - 多个流串联：A → B → C
    #   - 每个阶段是一个协程，通过流连接
    print("\n--- 示例4：管道式数据处理 ---")
    stage1_send, stage1_recv = anyio.create_memory_object_stream()
    stage2_send, stage2_recv = anyio.create_memory_object_stream()

    async def stage1_generate():
        """阶段1：生成原始数据"""
        for i in range(5):
            data = i * 10
            print(f"  [Stage1] 生成: {data}")
            await stage1_send.send(data)
            await anyio.sleep(0.1)
        await stage1_send.aclose()

    async def stage2_transform():
        """阶段2：转换数据"""
        async for raw in stage1_recv:
            transformed = raw + 1
            print(f"  [Stage2] 转换: {raw} -> {transformed}")
            await stage2_send.send(transformed)
        await stage2_send.aclose()

    async def stage3_output():
        """阶段3：输出结果"""
        async for data in stage2_recv:
            print(f"  [Stage3] 输出: {data}")

    async with anyio.create_task_group() as tg:
        tg.start_soon(stage1_generate)
        tg.start_soon(stage2_transform)
        tg.start_soon(stage3_output)
    print("  管道处理完成")

    # 示例5：send_nowait / receive_nowait 非阻塞操作
    #   - 缓冲区满时 send_nowait 抛出 WouldBlock
    #   - 无数据时 receive_nowait 抛出 WouldBlock
    print("\n--- 示例5：非阻塞 send_nowait / receive_nowait ---")
    send_nb, recv_nb = anyio.create_memory_object_stream(max_buffer_size=1)

    # 发送一条填满缓冲区
    await send_nb.send("first")
    print("  已发送 'first'，缓冲区已满")

    try:
        send_nb.send_nowait("second")
    except anyio.WouldBlock:
        print("  send_nowait 失败: WouldBlock（缓冲区满）")

    # 接收一条释放缓冲区
    msg = await recv_nb.receive()
    print(f"  接收: {msg}")

    # 现在可以发送了
    send_nb.send_nowait("second")
    print("  send_nowait 成功: 'second' 已发送")

    # receive_nowait
    msg = recv_nb.receive_nowait()
    print(f"  receive_nowait: {msg}")

    try:
        recv_nb.receive_nowait()
    except anyio.WouldBlock:
        print("  receive_nowait 失败: WouldBlock（无数据）")

    await send_nb.aclose()
    await recv_nb.aclose()


async def thread_usage():
    """
    AnyIO 线程交互使用。

    基本说明：
      - AnyIO 提供 anyio.to_thread.run_sync() 将同步阻塞函数放到线程池中执行。
      - 与 asyncio.loop.run_in_executor() 类似，但 API 更简洁、跨后端可移植。
      - 适合将现有的同步阻塞代码（如 requests、同步文件IO）集成到异步应用中。

    核心 API：
      - anyio.to_thread.run_sync(func, *args, abandon_on_cancel=False, limiter=None)：
        在线程池中执行同步函数，返回可 await 的对象。
        abandon_on_cancel=True 时，取消协程会放弃线程结果（线程继续运行但结果被丢弃）。
        limiter 参数可限制并发线程数（使用 CapacityLimiter）。

    注意事项：
      - 线程中不能直接调用 AnyIO 的异步 API（如 anyio.sleep()），会报错。
      - 线程与协程间的数据共享需要加锁（如 threading.Lock），AnyIO 同步原语不是线程安全的。
      - 如需协作取消，使用 threading.Event 手动通知线程检查。
      - 默认线程池大小由 AnyIO 管理，通常为 40 个线程。
      - 使用 CapacityLimiter 可以限制同时运行的线程数，避免资源耗尽。

    FAQ：
      Q: anyio.to_thread.run_sync() vs asyncio.loop.run_in_executor()？
      A: 总结如下：
         ┌──────────────────────┬─────────────────────────────────┬──────────────────────────────┐
         │       特性            │  asyncio.run_in_executor()      │  anyio.to_thread.run_sync()  │
         ├──────────────────────┼─────────────────────────────────┼──────────────────────────────┤
         │  跨后端               │  仅 asyncio                     │  asyncio/trio 均可            │
         │  取消支持             │  不支持取消线程                  │  abandon_on_cancel=True       │
         │  并发限制             │  需手动管理 ThreadPoolExecutor   │  limiter=CapacityLimiter      │
         │  语法                 │  需获取 loop 对象                │  直接调用，更简洁              │
         └──────────────────────┴─────────────────────────────────┴──────────────────────────────┘

      Q: 何时使用 abandon_on_cancel=True？
      A: 当线程执行时间可能很长，且你希望取消时能立即返回而不等待线程完成。
         注意：线程本身不会被中断，如需协作取消，使用 threading.Event 手动通知。
    """
    print("\n\n=== thread_usage ===")
    import time
    import threading

    # 辅助函数：模拟同步阻塞操作
    def blocking_io_work(name: str, delay: float):
        """模拟阻塞IO操作（如 requests.get、同步文件读写）"""
        print(f"  [{name}] 阻塞IO开始 (线程: {threading.current_thread().name})...")
        time.sleep(delay)  # 阻塞 sleep，不是 anyio.sleep
        print(f"  [{name}] 阻塞IO完成")
        return f"{name}-io-result"

    def cpu_work(name: str, n: int):
        """模拟CPU密集型操作"""
        print(f"  [{name}] CPU计算开始 (线程: {threading.current_thread().name})...")
        total = sum(i * i for i in range(n * 1_000_000))
        print(f"  [{name}] CPU计算完成")
        return total

    # 示例1：基本使用 - 将阻塞函数放到线程池
    #   - run_sync() 在线程池中执行同步函数，协程不会阻塞事件循环
    #   - 直接 await 获取返回值
    print("\n--- 示例1：基本线程执行 ---")
    result = await anyio.to_thread.run_sync(blocking_io_work, "IO-Task", 1.0)
    print(f"  结果: {result}")

    # 示例2：并发执行多个阻塞任务
    #   - 多个 run_sync 配合 TaskGroup 并发执行
    #   - 3个任务在3个不同线程中并发，总耗时 ≈ max(各任务耗时)
    print("\n--- 示例2：并发执行多个阻塞任务 ---")
    async with anyio.create_task_group() as tg:
        results = []

        async def run_and_collect(name: str, delay: float):
            r = await anyio.to_thread.run_sync(blocking_io_work, name, delay)
            results.append(r)

        tg.start_soon(run_and_collect, "IO-A", 0.5)
        tg.start_soon(run_and_collect, "IO-B", 0.5)
        tg.start_soon(run_and_collect, "IO-C", 0.5)
    print(f"  所有结果: {results}")
    print("  注意：3个阻塞任务在3个线程中并发，总耗时约0.5s而非1.5s")

    # 示例3：使用 CapacityLimiter 限制并发线程数
    #   - 避免同时创建过多线程耗尽系统资源
    #   - 4个任务，但最多2个线程同时运行
    print("\n--- 示例3：CapacityLimiter 限制并发线程 ---")
    limiter = anyio.CapacityLimiter(2)

    async with anyio.create_task_group() as tg:
        for i in range(4):
            tg.start_soon(
                lambda i=i: anyio.to_thread.run_sync(
                    blocking_io_work, f"Limited-{i}", 0.3, limiter=limiter
                )
            )
    print("  注意：最多2个线程同时运行，其余排队")

    # 示例4：可取消的线程操作
    #   - abandon_on_cancel=True：取消时放弃线程结果（线程继续运行但结果被丢弃）
    #   - 如需协作取消，使用 threading.Event 手动通知线程
    print("\n--- 示例4：可取消的线程操作 ---")

    cancel_event = threading.Event()

    def cancellable_work(name: str, delay: float):
        """可被取消的同步工作"""
        print(f"  [{name}] 开始 (可取消)...")
        start = time.time()
        while time.time() - start < delay:
            time.sleep(0.1)
            # 检查是否被请求取消
            if cancel_event.is_set():
                print(f"  [{name}] 检测到取消请求，提前退出")
                return f"{name}-cancelled"
        print(f"  [{name}] 正常完成")
        return f"{name}-done"

    try:
        with anyio.fail_after(0.5):  # 0.5s 超时
            result = await anyio.to_thread.run_sync(
                cancellable_work, "CancelTask", 3.0, abandon_on_cancel=True
            )
            print(f"  结果: {result}")
    except TimeoutError:
        cancel_event.set()  # 通知线程取消
        print("  线程操作被取消（fail_after 超时）")

    # 示例5：线程中不能调用 AnyIO 异步 API
    #   - 在 run_sync 的回调中调用 anyio.sleep() 会报错
    #   - 需要使用对应的同步 API（如 time.sleep()）
    print("\n--- 示例5：线程中不能调用异步API ---")
    def bad_thread_func():
        print("  在线程中...")
        # anyio.sleep(0.1)  # ← 这会报错！线程中没有事件循环
        time.sleep(0.1)  # 正确：使用同步 API
        print("  线程工作完成")
        return "ok"

    result = await anyio.to_thread.run_sync(bad_thread_func)
    print(f"  结果: {result}")
    print("  注意：线程中必须使用同步API（time.sleep），不能用 anyio.sleep")

    # 示例6：线程间共享数据（需要线程安全锁）
    print("\n--- 示例6：线程间共享数据 ---")
    thread_lock = threading.Lock()
    shared_list = []

    def thread_safe_append(name: str, value: int):
        with thread_lock:
            shared_list.append((name, value))
            print(f"  [{name}] 追加: {value}, 当前列表: {shared_list}")
        time.sleep(0.1)
        return value

    async with anyio.create_task_group() as tg:
        for i in range(3):
            tg.start_soon(
                lambda i=i: anyio.to_thread.run_sync(
                    thread_safe_append, f"Thread-{i}", i * 10
                )
            )
    print(f"  最终列表: {shared_list}")
    print("  注意：使用 threading.Lock 而非 anyio.Lock（后者不是线程安全的）")


async def subprocess_usage():
    """
    AnyIO 进程交互使用。

    基本说明：
      - AnyIO 提供 anyio.run_process() 和 anyio.open_process() 用于异步子进程管理。
      - 与 asyncio.create_subprocess_exec() 类似，但 API 更简洁、跨后端可移植。
      - 支持标准输入/输出/错误的流式处理。

    核心 API：
      - anyio.run_process(command, *, input=None, check=True, ...)：
        运行命令并等待完成，返回 CompletedProcess 对象。
        类似 subprocess.run() 但异步执行。
      - anyio.open_process(command, *, ...)：
        异步上下文管理器，返回可交互的 Process 对象。
        可通过 process.stdin/stdout/stderr 流式读写。

    注意事项：
      - run_process() 适合一次性命令，open_process() 适合需要交互的长时间进程。
      - 子进程的取消：取消协程会向子进程发送终止信号（Windows: TerminateProcess, Unix: SIGKILL）。
      - 默认工作目录是当前工作目录，可通过 cwd 参数修改。
      - 环境变量可通过 env 参数传递，默认继承当前进程的环境变量。
      - 在 Windows 上，command 可以是字符串（由 shell 解析）或列表。

    FAQ：
      Q: anyio.run_process() vs asyncio.create_subprocess_exec()？
      A: 总结如下：
         ┌──────────────────────┬─────────────────────────────────┬──────────────────────────────┐
         │       特性            │  asyncio subprocess             │  anyio subprocess            │
         ├──────────────────────┼─────────────────────────────────┼──────────────────────────────┤
         │  跨后端               │  仅 asyncio                     │  asyncio/trio 均可            │
         │  简单命令             │  需手动创建+等待+通信            │  run_process() 一步到位       │
         │  交互式进程           │  create_subprocess_exec()       │  open_process() 上下文管理器  │
         │  取消处理             │  需手动 terminate/kill           │  自动终止子进程               │
         │  超时                 │  需配合 wait_for                 │  内置 cancel_scope 支持       │
         └──────────────────────┴─────────────────────────────────┴──────────────────────────────┘

      Q: run_process() vs open_process() 的选择？
      A: run_process()：一次性命令，等待完成获取结果（如 git status、ls -la）。
         open_process()：需要与进程交互（如逐行读取输出、发送输入），或长时间运行的进程。
    """
    print("\n\n=== subprocess_usage ===")

    # 示例1：run_process 基本使用 - 执行简单命令
    #   - 类似 subprocess.run()，但异步执行不阻塞事件循环
    #   - 返回 CompletedProcess 对象，包含 stdout/stderr/returncode
    print("\n--- 示例1：run_process 基本使用 ---")
    result = await anyio.run_process(
        [sys.executable, "-c", "print('hello from subprocess')"],
    )
    print(f"  返回码: {result.returncode}")
    print(f"  标准输出: {result.stdout.decode(errors='replace').strip()}")

    # 示例2：run_process 捕获 stderr 和错误处理
    #   - check=False 时不因非零返回码抛异常
    print("\n--- 示例2：run_process 错误处理 ---")
    result = await anyio.run_process(
        [sys.executable, "-c",
         "import sys; print('to stdout'); print('to stderr', file=sys.stderr); sys.exit(42)"],
        check=False,
    )
    print(f"  返回码: {result.returncode}")
    print(f"  stdout: {result.stdout.decode(errors='replace').strip()}")
    print(f"  stderr: {result.stderr.decode(errors='replace').strip()}")

    # 示例3：run_process 传递输入数据
    print("\n--- 示例3：run_process 传递输入 ---")
    result = await anyio.run_process(
        [sys.executable, "-c", "import sys; data = sys.stdin.read(); print(f'收到: {data}')"],
        input=b"hello from parent process",
    )
    print(f"  子进程输出: {result.stdout.decode(errors='replace').strip()}")

    # 示例4：open_process 交互式进程
    #   注意：Windows 上 anyio.open_process 对交互式子进程支持有限，
    #   推荐使用 anyio.run_process() + input 参数替代简单交互场景。
    print("\n--- 示例4：open_process 交互式进程 ---")
    # 使用 run_process + input 模拟交互式进程
    result = await anyio.run_process(
        [sys.executable, "-c",
         "import sys\n"
         "data = sys.stdin.read()\n"
         "print('READY')\n"
         "for line in data.splitlines():\n"
         "    print(f'ECHO: {line}')\n"
         "    if 'EXIT' in line: break\n"
         ],
        input=b"hello\nworld\nEXIT\n",
        check=False,
    )
    print(f"  返回码: {result.returncode}")
    if result.stderr:
        print(f"  stderr: {result.stderr.decode(errors='replace').strip()}")
    for line in result.stdout.decode(errors='replace').strip().split('\n'):
        print(f"  {line}")
    print("  交互式进程已退出")

    # 示例5：并发执行多个子进程
    print("\n--- 示例5：并发执行多个子进程 ---")
    async def run_command(cmd_id: int, delay: float):
        result = await anyio.run_process(
            [sys.executable, "-c",
             f"import time; time.sleep({delay}); print(f'Task-{cmd_id} done')"],
        )
        return f"Task-{cmd_id}: {result.stdout.decode(errors='replace').strip()}"

    async with anyio.create_task_group() as tg:
        results = []
        async def run_and_store(cmd_id: int, delay: float):
            r = await run_command(cmd_id, delay)
            results.append(r)
        tg.start_soon(run_and_store, 1, 0.3)
        tg.start_soon(run_and_store, 2, 0.2)
        tg.start_soon(run_and_store, 3, 0.1)
    for r in results:
        print(f"  {r}")
    print("  注意：3个子进程并发执行，总耗时约0.3s")

    # 示例6：子进程超时取消
    print("\n--- 示例6：子进程超时取消 ---")
    try:
        with anyio.fail_after(0.5):
            result = await anyio.run_process(
                [sys.executable, "-c", "import time; time.sleep(10); print('never')"],
            )
    except TimeoutError:
        print("  子进程因超时被终止")
    print("  注意：AnyIO 自动终止了超时的子进程")

    # 示例7：传递环境变量
    print("\n--- 示例7：传递环境变量 ---")
    result = await anyio.run_process(
        [sys.executable, "-c", "import os; print(os.environ.get('MY_VAR', 'NOT_SET'))"],
        env={"MY_VAR": "hello-anyio", **dict(os.environ)},
    )
    print(f"  子进程读取环境变量: {result.stdout.decode(errors='replace').strip()}")


async def file_io_usage():
    """
    AnyIO 文件异步IO使用。

    基本说明：
      - AnyIO 提供 anyio.Path 和 anyio.open_file() 用于异步文件操作。
      - 与 aiofiles 类似，但集成在 AnyIO 中，无需额外安装。
      - 支持异步读写、文件系统操作（stat、mkdir、glob 等）。
      - 提供 anyio.TemporaryDirectory / anyio.NamedTemporaryFile 用于异步临时文件/目录。

    核心 API：
      - anyio.Path(path)：异步路径对象，类似 pathlib.Path 但方法都是异步的。
      - await anyio.Path(path).read_text() / read_bytes()：异步读取文件内容。
      - await anyio.Path(path).write_text(data) / write_bytes(data)：异步写入文件。
      - async with await anyio.open_file(path, mode)：异步打开文件，返回异步文件对象。
      - 异步文件对象支持：await f.read(n)、await f.write(data)、async for line in f 等。
      - async with anyio.TemporaryDirectory(...) as tmp_dir：异步临时目录，自动清理。
      - async with anyio.NamedTemporaryFile(...) as f：异步临时文件，自动清理。

    注意事项：
      - AnyIO 的异步文件IO在不同后端有不同实现：
        asyncio 后端使用线程池（默认），trio 后端使用真正的异步IO。
      - 在 asyncio 后端下，异步文件操作实际上是在线程池中执行的。
      - 对于大文件，使用 async for line in f 逐行读取避免内存溢出。
      - anyio.Path 的方法与 pathlib.Path 基本对应，但都是协程需要 await。
      - 文件操作可能抛出 OSError（如文件不存在、权限不足等）。
      - anyio.TemporaryDirectory 退出 async with 块时自动清理目录，无需手动删除。

    FAQ：
      Q: anyio.Path vs aiofiles？
      A: anyio.Path 是 AnyIO 内置的，无需额外依赖。
         aiofiles 是独立的第三方库，功能更丰富（如支持更多文件模式）。
         如果已使用 AnyIO，推荐优先使用 anyio.Path。

      Q: 异步文件IO真的比同步快吗？
      A: 对于单个文件操作，异步文件IO不会更快（底层仍是系统调用）。
         优势在于：多个文件操作可以并发执行，且不会阻塞事件循环中的其他协程。
         在 asyncio 后端下，文件操作在线程池中执行，本质上是把阻塞操作移到后台线程。

      Q: 如何并发读写多个文件？
      A: 使用 TaskGroup 并发执行多个 anyio.Path 操作。
         每个操作在线程池中独立执行，不会相互阻塞。

      Q: anyio.TemporaryDirectory vs tempfile.mkdtemp？
      A: anyio.TemporaryDirectory 是异步上下文管理器，自动在后台线程中创建和清理。
         优势：无需手动 try/finally + shutil.rmtree()，且不阻塞事件循环。
    """
    print("\n\n=== file_io_usage ===")

    # 使用 anyio.TemporaryDirectory 创建临时目录（自动清理）
    #   - async with 进入时在后台线程创建目录
    #   - async with 退出时在后台线程自动删除目录
    #   - 无需手动 try/finally + shutil.rmtree()
    async with anyio.TemporaryDirectory(prefix="anyio_demo_") as tmp_dir:
        print(f"  临时目录: {tmp_dir}")

        # 示例1：anyio.Path 基本读写
        #   - anyio.Path 类似 pathlib.Path，但方法需要 await
        #   - read_text() / write_text() 异步读写文本
        print("\n--- 示例1：anyio.Path 基本读写 ---")
        file_path = anyio.Path(tmp_dir) / "hello.txt"
        await file_path.write_text("Hello, AnyIO!\n第二行内容")
        print(f"  写入文件: {file_path}")

        content = await file_path.read_text()
        print(f"  读取内容:\n{content}")

        # 示例2：anyio.open_file 流式读写
        #   - async with await anyio.open_file() 异步打开文件
        #   - 支持逐行读取、分块读取
        print("\n--- 示例2：anyio.open_file 流式读写 ---")
        large_file = anyio.Path(tmp_dir) / "large.txt"
        # 写入多行数据
        lines_data = "\n".join(f"line-{i:04d}" for i in range(10))
        await large_file.write_text(lines_data)

        # 逐行读取
        print("  逐行读取:")
        async with await anyio.open_file(large_file, "r") as f:
            count = 0
            async for line in f:
                count += 1
                if count <= 3:  # 只打印前3行
                    print(f"    {line.rstrip()}")
        print(f"  共读取 {count} 行")

        # 分块读取二进制文件
        print("\n  分块读取二进制:")
        bin_file = anyio.Path(tmp_dir) / "data.bin"
        await bin_file.write_bytes(b"\x00\x01\x02\x03" * 25)  # 100字节
        async with await anyio.open_file(bin_file, "rb") as f:
            chunk = await f.read(10)
            print(f"    第一块(10字节): {chunk.hex()}")
            chunk = await f.read(10)
            print(f"    第二块(10字节): {chunk.hex()}")

        # 示例3：文件系统操作
        #   - mkdir、exists、is_file、is_dir、glob 等
        print("\n--- 示例3：文件系统操作 ---")
        sub_dir = anyio.Path(tmp_dir) / "subdir"
        await sub_dir.mkdir(exist_ok=True)
        print(f"  创建目录: {sub_dir}")

        # 创建几个文件
        for i in range(3):
            f = sub_dir / f"file_{i}.txt"
            await f.write_text(f"content-{i}")

        # glob 查找文件
        print("  glob 查找 *.txt:")
        async for f in sub_dir.glob("*.txt"):
            stat = await f.stat()
            print(f"    {f.name} (大小: {stat.st_size} bytes)")

        # 检查路径属性
        print(f"  sub_dir 是目录: {await sub_dir.is_dir()}")
        print(f"  sub_dir 是文件: {await sub_dir.is_file()}")

        # 示例4：并发读写多个文件
        #   - 使用 TaskGroup 并发操作多个文件
        #   - 每个文件操作在线程池中独立执行
        print("\n--- 示例4：并发读写多个文件 ---")
        async def write_and_read(index: int):
            f = anyio.Path(tmp_dir) / f"concurrent_{index}.txt"
            data = f"data-from-task-{index}" * 100  # 制造一些数据量
            await f.write_text(data)
            read_back = await f.read_text()
            return f"file_{index}: wrote {len(data)} chars, read {len(read_back)} chars"

        async with anyio.create_task_group() as tg:
            results = []
            async def collect(index: int):
                r = await write_and_read(index)
                results.append(r)
            for i in range(5):
                tg.start_soon(collect, i)
        for r in sorted(results):
            print(f"    {r}")
        print("  注意：5个文件并发读写，不会相互阻塞")

        # 示例5：文件复制（读+写）
        print("\n--- 示例5：文件复制 ---")
        src = anyio.Path(tmp_dir) / "hello.txt"
        dst = anyio.Path(tmp_dir) / "hello_copy.txt"
        content = await src.read_bytes()
        await dst.write_bytes(content)
        print(f"  复制: {src.name} -> {dst.name}")
        print(f"  验证: {(await dst.read_text()).strip()}")

        # 示例6：错误处理
        print("\n--- 示例6：错误处理 ---")
        nonexistent = anyio.Path(tmp_dir) / "nonexistent.txt"
        try:
            await nonexistent.read_text()
        except FileNotFoundError as e:
            print(f"  文件不存在: {e}")

        # 示例7：对比 - 同步文件操作会阻塞事件循环
        print("\n--- 示例7：对比同步文件操作 ---")
        print("  同步 open()/read() 会阻塞事件循环线程")
        print("  AnyIO 的 anyio.Path 在线程池中执行，不阻塞事件循环")
        print("  推荐在异步代码中始终使用 anyio.Path 而非内置 open()")

        # 示例8：anyio.NamedTemporaryFile 异步临时文件
        #   - async with 进入时创建临时文件，退出时自动删除
        #   - 返回 AsyncFile 对象，支持异步读写
        print("\n--- 示例8：anyio.NamedTemporaryFile 临时文件 ---")
        async with anyio.NamedTemporaryFile(
            mode="w+", suffix=".txt", prefix="anyio_tmp_", dir=tmp_dir
        ) as tmp_file:
            file_name = tmp_file.name
            print(f"  临时文件名: {file_name}")
            # 写入数据
            await tmp_file.write("临时文件内容\n第二行")
            await tmp_file.flush()
            # 回到开头读取
            await tmp_file.seek(0)
            content = await tmp_file.read()
            print(f"  读取内容:\n{content}")
        # 退出 async with 后文件已自动删除
        print(f"  退出后文件是否存在: {await anyio.Path(file_name).exists()}")

    # 退出 async with TemporaryDirectory 后目录已自动清理
    print(f"\n  退出后临时目录是否存在: {await anyio.Path(tmp_dir).exists()}")
    print("  注意：anyio.TemporaryDirectory 自动清理，无需手动 shutil.rmtree()")


async def main():
    """调试入口函数"""
    await structured_concurrency_basic_usage()
    await structured_concurrency_exception_usage()
    await structured_concurrency_cancellation_usage()
    await structured_concurrency_combination_usage()
    await synchronization_primitive_usage()
    await stream_usage()
    await thread_usage()
    await subprocess_usage()
    await file_io_usage()
    

if __name__ == "__main__":
    asyncio.run(main())
