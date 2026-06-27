"""
研究AnyIO使用。
以 anyio v1.14.0 + 版本为例。
"""
import os
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
      - start() 要求子任务函数签名包含 task_status: TaskStatus 参数，且必须调用 task_status.started()。
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
        """通过 task_status.started() 通知调用方"我已就绪" """
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
    """
    print("\n\n=== synchronization_primitive_usage ===")
    

async def stream_usage():
    """
    AnyIO Stream封装使用。
    """
    print("\n\n=== stream_usage ===")
    

async def thread_usage():
    """
    AnyIO 线程交互使用。
    """
    print("\n\n=== thread_usage ===")


async def thread_and_subprocess_usage():
    """
    AnyIO 进程交互使用。
    """
    print("\n\n=== subprocess_usage ===")


async def file_io_usage():
    """
    AnyIO 文件异步IO使用。
    """
    print("\n\n=== file_io_usage ===")


async def main():
    """调试入口函数"""
    await structured_concurrency_basic_usage()
    await structured_concurrency_exception_usage()
    await structured_concurrency_cancellation_usage()
    await structured_concurrency_combination_usage()
    # 以下函数待补充
    # await synchronization_primitive_usage()
    # await stream_usage()
    # await thread_usage()
    # await subprocess_usage()
    # await file_io_usage()
    

if __name__ == "__main__":
    asyncio.run(main())
