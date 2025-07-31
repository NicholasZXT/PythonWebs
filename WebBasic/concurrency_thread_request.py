"""
使用 ThreadPoolExecutor + request.Session 实现多线程会话复用的实践。
下述方案是结合 Qwen3 + Gemini 2.5 Pro 多次讨论得到。
此方案涉及和解决的技术点如下：
- 多次请求同一域名；需要登录态；共享请求配置（请求头等）时，使用 requests.Session 比直接使用 request.get/post 方法性能好，
  因为 requests.Session 可以复用TCP连接（3次握手 + TLS 握手 ≈ 100ms~300ms），但是 **requests.Session 不是线程安全的**。
- 使用 ThreadPoolExecutor 时，线程调用的 Callable 对象里，每次都创建一个 Session，开销依然很大。
- 使用 ThreadPoolExecutor 初始化时的 initializer 参数，定义每个线程初始化时的操作。
  - 最大的问题在于 initializer 的返回值会被忽略，也就是无法将初始化的 Session 对象传递给线程后续的 Callable 对象 —— 除非借助 threading.local()。
  - 依旧无法在线程结束时执行 Session.close()。
- 使用 ThreadPoolExecutor + threading.local()，在 threading.local() 里保存线程池里每个线程对应的 Session 对象。
  - 此方案较为可行。
  - 最大的问题是没办法关闭 Session。
- 使用下面的方案，实现多线程下的 ThreadPoolExecutor + threading.local() 复用 Session，并合理关闭 Session。
"""

import threading
import requests
from concurrent.futures import ThreadPoolExecutor


class ThreadSafeSessionManager:
    """
    一个完全线程安全的 Session 管理器。
    它使用锁来保护 Session 的创建和注册过程，防止竞态条件。
    支持自定义请求 headers。
    """

    def __init__(self, headers: dict | None = None):
        # 关于 threading.local()，它里面的保存的引用的生命周期和线程是一样的：一旦线程结束，那么它在 threading.local 里保存的引用对象也会被删除 。
        self._thread_local = threading.local()
        # 这个列表用于保存所有创建的 Session 对象，以便在关闭时进行清理。
        self._all_sessions = []
        # 关键：为临界区创建一个锁 —— 主要是用于保护上面 self._all_sessions 列表的多线程访问。
        self._lock = threading.Lock()
        # 存储用户自定义的 headers
        self._headers = headers or {}
        print("Session Manager initialized with Lock.")

    def get_session(self):
        """为当前线程获取或创建 Session。"""
        # 首次检查，无锁，为了性能。大多数情况下 session 已存在，可直接返回。
        if hasattr(self._thread_local, 'session'):
            return self._thread_local.session

        # 如果 session 不存在，则进入需要同步的临界区
        with self._lock:
            # 关键：双重检查锁定 (Double-Checked Locking)
            # 获取锁后必须再次检查，因为可能在等待锁的时候，其他线程已经创建了 session。
            # 如果没有这第二次检查，所有等待锁的线程最终都会创建一个新的 Session，锁就失去了意义。
            if not hasattr(self._thread_local, 'session'):
                session = requests.Session()
                # 应用自定义 headers
                session.headers.update(self._headers)
                print(f"[Thread {threading.get_ident()}] Creating and registering a new Session.")
                self._all_sessions.append(session)
                self._thread_local.session = session

        return self._thread_local.session

    def close_all(self):
        """关闭所有已注册的 Session。"""
        print("\n--- Manager is closing all sessions. ---")
        if not self._all_sessions:
            print("No sessions were created to close.")
            return

        print(f"Closing {len(self._all_sessions)} sessions...")
        for session in self._all_sessions:
            # 关闭会话时增加了异常捕获，以确保即使某些会话关闭失败也不会影响其他会话的关闭操作。
            try:
                session.close()
                print(f"closed session: {session}.")
            except Exception as e:
                print(f"Error closing session: {e}")
        # 清空列表，避免残留引用
        self._all_sessions.clear()
        print("--- All sessions are closed. ---")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_all()


# 使用上下文管理器的主逻辑
def worker_with_manager(manager: ThreadSafeSessionManager, url: str, data: dict | None = None):
    """一个使用 Session 管理器的工作任务"""
    try:
        session = manager.get_session()
        print(f"[Thread {threading.get_ident()}] get session {session}.")
        response = session.post(url, data=data)
        print(f"[Thread {threading.get_ident()}] Fetched {url}, Status: {response.status_code}")
    except requests.RequestException as e:
        print(f"[Thread {threading.get_ident()}] Error fetching {url}: {e}")


if __name__ == "__main__":
    from copy import deepcopy
    url = 'http://localhost:10086/v1/chat/completions'
    headers = {'Content-Type': 'application/json', "Accept": "application/json"}
    payload = {
        'model': 'Qwen3-7B',
        'messages': [
            {'role': 'system', 'content': 'You are a helpful assistant'},
            {"role": "user", "content": ''}
        ],
        'max_tokens': 512,
        'top_p': 0.9,
        'temperature': 0.1,
    }
    contents = [
        "请给一个Python requests 库的使用示例，并给出代码注释。",
        "请给一个Python httpx 库的使用示例，并给出代码注释。",
        "请给一个Python aiohttp 库的使用示例，并给出代码注释。",
        "请给一个Python ruff 库的使用示例，并给出代码注释。"
    ]
    payloads = []
    for content in contents:
        data = deepcopy(payload)
        data['messages'][1]['content'] = content
        payloads.append(data)

    print("--- Starting execution with Session Manager ---")
    # 使用 with 语句，自动管理 SessionManager 的生命周期
    with ThreadSafeSessionManager(headers=headers) as manager:
        with ThreadPoolExecutor(max_workers=2) as executor:
            tasks = [executor.submit(worker_with_manager, manager, url, data) for data in payloads]
            # 等待所有任务完成
            for future in tasks:
                future.result()

    print("\n--- Program finished. ---")
