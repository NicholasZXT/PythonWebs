"""
Litestar 自定义中间件。
Litestar中有如下3种创建中间件的方式：
（1）定义一个高阶函数，函数签名为 Callable[[ASGIApp], ASGIApp]，也就是接受一个 ASGIApp 的参数，返回一个 ASGIApp
（2）直接继承 ASGIMiddleware，这是 v2.15 版本开始提供的组件 —— 最为推荐
（3）使用 MiddlewareProtocol/AbstractMiddleware ，早期版本的方式
"""
from litestar.enums import ScopeType
from litestar.middleware import ASGIMiddleware, AbstractMiddleware
from litestar.datastructures import MutableScopeHeaders
from litestar.types import ASGIApp, Message, Receive, Scope, Send
import time

# ------------------------- 方式1 ----------------------------
def middleware_factory(app: ASGIApp) -> ASGIApp:
    print(">>> Middleware factory called...")

    async def my_middleware(scope: Scope, receive: Receive, send: Send) -> None:
        # do something here
        print(">>> my_middleware called...")
        await app(scope, receive, send)
    return my_middleware


# ------------------------- 方式2 ----------------------------
class ProcessTimeHeader(ASGIMiddleware):
    scopes = (ScopeType.HTTP, ScopeType.ASGI)

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        start_time = time.monotonic()

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                process_time = time.monotonic() - start_time
                headers = MutableScopeHeaders.from_message(message=message)
                headers["X-Process-Time"] = str(process_time)
            await send(message)

        await next_app(scope, receive, send_wrapper)


# ------------------------- 方式3 ----------------------------
class MyMiddleware(AbstractMiddleware):
    scopes = {ScopeType.HTTP}
    exclude = ["first_path", "second_path"]
    exclude_opt_key = "exclude_from_middleware"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        start_time = time.monotonic()

        async def send_wrapper(message: "Message") -> None:
            if message["type"] == "http.response.start":
                process_time = time.monotonic() - start_time
                headers = MutableScopeHeaders.from_message(message=message)
                headers["X-Process-Time"] = str(process_time)
            await send(message)

        await self.app(scope, receive, send_wrapper)
