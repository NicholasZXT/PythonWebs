"""
展示在FastAPI等异步网络框架里，如何正确执行异步批量处理任务。

Python中异步（网络）编程 **大部分场景** 使用要点可以总结为如下：
  - 使用Python的异步网络框架（比如 Starlette/FastAPI，tornado）时，在异步视图函数里，绝大多数场景下只需要一直嵌套await一个协程函数；
  - 最重要的点在于这一系列的嵌套await调用里，绝对不要使用任何阻塞IO的API（比如requests库），保证不阻塞事件循环的线程即可；
  - 实际的异步并发体现在异步网络框架（比如 Starlette）会将我们写的异步视图函数封装为 Task，借助事件循环来异步并发执行；
  - 当我们写的异步视图函数里await执行到一个需要等待的异步操作（如网络请求、文件读写、定时器）时，异步网络框架会借助底层的事件循环来暂停当前协程，
    并恢复其他已就绪的协程（例如：之前另一个请求等待的 IO 已完成），从而实现并发。

对于确实需要在视图函数里创建异步并发任务的情况，比如 需要调用多个其他的网络服务处理任务 / 需要对一批数据调用同一个网络服务进行处理 这样的场景，
可以采用如下方案。
(1) 使用 asyncio 事件循环的 run_in_executor() + concurrent.futures.ThreadPoolExecutor() + requests
(2) 使用 asyncio 的 gather()/wait()/as_completed() + asyncio.create_task() + httpx.AsyncClient
方案(1) 是“用多线程模拟异步”，不是真正的异步，有线程上下文切换的开销
方案(2) 是真正的异步，与异步框架天然契合，比较推荐。

此外，可以直接在视图函数里使用 asyncio 提供的大部分API（除了asyncio.run()），因为 Starlette 框架底层运行时已经创建了一个 asyncio 的事件循环。
"""
from typing import List
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Path, Query, Body, Request, status
from fastapi.responses import Response, JSONResponse, PlainTextResponse, HTMLResponse
from fastapi.encoders import jsonable_encoder
import requests
import httpx

batch_router = APIRouter(
    prefix='/batch',
    tags=['Batch-Process-Async']
)

# ===================== 服务模拟 ===============================
# --------- 使用 requests 库的同步请求服务 -------
async def save_to_mysql_mock_sync(data):
    # 使用 requests（阻塞）
    res = requests.get("https://www.baidu.com")
    return "mysql_mock_sync"

async def save_to_es_mock_sync(data):
    res = requests.get("https://www.baidu.com")
    return "es_mock_sync"

async def call_model_service_mock_sync(data):
    res = requests.get("https://www.baidu.com")
    return "model_service_mock_sync"

# ----------- 使用 httpx 库的异步请求服务 -------
# 一个优化点是复用 httpx.AsyncClient()对象，通过依赖注入的方式
async def save_to_mysql_mock_async(data):
    async with httpx.AsyncClient() as client:
        res = await client.get("https://www.baidu.com")
    return "mysql_mock_async"

async def save_to_es_mock_async(data):
    async with httpx.AsyncClient() as client:
        res = await client.get("https://www.baidu.com")
    return "es_mock_async"

async def call_model_service_mock_async(data):
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://www.baidu.com")
    return "model_service_mock_async"


# ===================== 方案一 ===============================
@batch_router.get('/executor')
async def batch_process_by_executor():
    data = "some data"
    executor = ThreadPoolExecutor(max_workers=10)
    loop = asyncio.get_running_loop()
    # 并发执行三个任务
    r1, r2, r3 = await asyncio.gather(
        loop.run_in_executor(executor, save_to_mysql_mock_sync, data),
        loop.run_in_executor(executor, save_to_es_mock_sync, data),
        loop.run_in_executor(executor, call_model_service_mock_sync, data),
    )
    print(f"r1: {r1}, r2: {r2}, r3: {r3}")
    return {'r1': r1, 'r2': r2, 'r3': r3}


# ===================== 方案二 ===============================
@batch_router.get('/task')
async def batch_process_by_task():
    data = "some data"
    # 并发创建多种类型任务
    task1 = asyncio.create_task(save_to_mysql_mock_async(data))
    task2 = asyncio.create_task(save_to_es_mock_async(data))
    task3 = asyncio.create_task(call_model_service_mock_async(data))
    # 必须要 await
    r1 = await task1
    r2 = await task2
    r3 = await task3
    # 也可以直接用 gather，保证按照提交顺序返回结果
    # r1, r2, r3 = await asyncio.gather(task1, task2, task3)
    print(f"r1: {r1}, r2: {r2}, r3: {r3}")
    return {'r1': r1, 'r2': r2, 'r3': r3}

@batch_router.get('/gather')
async def batch_process_by_gather():
    data_batch = [1, 2, 3]
    # 并发创建同种类型任务，批量执行数据
    coroutines = [call_model_service_mock_async(item) for item in data_batch]
    results = await asyncio.gather(*coroutines)
    # 也可以返回失败的对象
    # results = await asyncio.gather(*coroutines, return_exceptions=True)
    return results

@batch_router.get('/as_completed')
async def batch_process_by_as_completed():
    data_batch = [1, 2, 3]
    coroutines = [call_model_service_mock_async(item) for item in data_batch]
    # 按 完成顺序 返回结果（生成器），适合“谁先完成谁先处理”场景
    for coro in asyncio.as_completed(coroutines):
        result = await coro
        print("Completed:", result)

@batch_router.get('/wait')
async def batch_process_by_wait():
    data_batch = [1, 2, 3]
    tasks = [asyncio.create_task(call_model_service_mock_async(item)) for item in data_batch]
    # 等待多个 Task，返回完成/未完成集合
    done, pending = await asyncio.wait(tasks)
    results = [task.result() for task in done]
    return results

@batch_router.get('/limit')
async def batch_process_with_limit():
    data_batch = [1, 2, 3]
    # 使用信号量来限制并发
    semaphore = asyncio.Semaphore(10)  # 最多 10 个并发

    async def call_with_limit(item):
        async with semaphore:
            return await call_model_service_mock_async(item)

    coroutines = [call_with_limit(item) for item in data_batch]
    results = await asyncio.gather(*coroutines)
    return results
