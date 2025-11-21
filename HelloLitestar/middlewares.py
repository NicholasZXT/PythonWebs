"""
Litestar 自定义中间件。

根据官方文档的说法，在 Litestar（和 Starlette/FastAPI）中，Middleware 本质是一个“中间 ASGI App”，
但是有一个特别的要求是 它必须要持有 下一个 ASGI App 的引用，因为在处理完本身的业务之后，还需要调用调用下一个 ASGI App。

在 Litestar 中，Middleware 的调用时机是在 应用入口 和 router handler function 之间。

Litestar中有如下3种创建中间件的方式：
（1）手动实现一个 ASGI App，也有两种方式：
    - 定义一个高阶函数，函数签名为 Callable[[ASGIApp], ASGIApp]，也就是接受一个 ASGIApp 的参数，返回一个 ASGIApp
    - 定义一个类，__call__ 方法的签名为 (self, scope, receive, send)
（2）使用 MiddlewareProtocol/AbstractMiddleware/DefineMiddleware —— 推荐使用，特别是 AbstractMiddleware
    - MiddlewareProtocol/AbstractMiddleware 两个需要继承
    - DefineMiddleware 不能继承
（3）继承 ASGIMiddleware，这是 v2.15 版本开始提供的组件，用于将任意 ASGI App 转为 Middleware，不太适合一般用户使用
"""
from typing import Any, Awaitable, Callable
from litestar.types import ASGIApp, Message, Receive, Scope, Send, Scopes
from litestar.enums import ScopeType
from litestar.datastructures import MutableScopeHeaders
from litestar.middleware import MiddlewareProtocol, AbstractMiddleware, ASGIMiddleware, DefineMiddleware
from litestar.middleware.rate_limit import RateLimitConfig
import time

# ------------------------- 方式1：手动实现ASGI App ----------------------------
# （1）基于高阶函数的方式实现中间件
def simple_middleware_factory(app: ASGIApp) -> ASGIApp:
    """
    这个高阶函数相当于一个简单工厂，主要作用就是接受下一个 ASGI App 实例，然后通过闭包引用的方式提供给自定义 ASGI App.
    """
    print(">>> Simple middleware factory called...")

    async def my_middleware_func(scope: Scope, receive: Receive, send: Send) -> None:
        """
        此函数就是一个满足ASGI协议的App。
        :param scope:
        :param receive:
        :param send:
        :return:
        """
        # ------ 可以对 scope、receive、send 做一些封装处理 -----
        print(">>> my_middleware called...")
        # 检查 scope 里的协议字段
        print("[my_middleware_func] scope[type]:", scope['type'])
        # 可以调用 receive 获取上一个 ASGI App 接受的数据
        # 可以调用 send 发送数据给下一个 ASGI App
        # ---------------------------------------------------

        # 相比于标准 ASGI App，唯一有区别的地方是下面：需要调用下一个 ASGI App，因为 Litestar 是以 ASGI App 链式调用来执行的
        # 这里拿到的下一个 ASGI App 实例就是外面高阶函数提供的，因为 ASGI 协议标准无法传入其他的参数了，因此需要通过高阶函数的方式获取
        await app(scope, receive, send)

    return my_middleware_func

# （2）基于类方式实现中间件，显得更为自然，因为下一个 ASGI App 可以作为实例属性保存
class SimpleClassMiddleware:
    def __init__(self, app):  # app 是下一个 ASGI App
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        print(">>> SimpleClassMiddleware called...")
        # 在调用下一个 app 前做事情（如记录日志）
        print("[SimpleClassMiddleware] → Request:", scope["path"])

        # 调用下一个 ASGI App
        await self.app(scope, receive, send)

        # 在之后做事情（但注意：send 已完成，通常无法修改响应）
        print("[SimpleClassMiddleware] ← Response sent")


# ------------------------- 方式2 ----------------------------
# （1）基于 MiddlewareProtocol 实现中间件，这个方式其实和方式1中的类实现一样，只不过通过 MiddlewareProtocol 这个协议类做了一些规范而已
class SimpleProtocolMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp, **kwargs: Any) -> None:  # app 是下一个 ASGI App
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        print(">>> SimpleProtocolMiddleware called...")
        print("[SimpleProtocolMiddleware] → Request:", scope["path"])
        # 调用下一个 ASGI App
        await self.app(scope, receive, send)
        print("[SimpleProtocolMiddleware] ← Response sent")


# （2）基于 AbstractMiddleware 实现中间件
class SimpleAbstractMiddleware(AbstractMiddleware):
    """
    AbstractMiddleware类提供了一些公共方法的实现和一些配置项
    """
    # 指定中间件的生效协议范围
    scopes = {ScopeType.HTTP}
    # 排除某些路由path
    exclude = ["/somepath"]
    # 自定义一个值，可以在 route handler 里通过 Router.opt 字典获取，由路由函数借此检查是否需要跳过此中间件的执行
    # 具体来说，就是这里设置的值，如果在 @get()/@post() 中添加了参数 exclude_from_middleware=True，则该视图函数就会跳过此中间件的执行
    exclude_opt_key = "exclude_from_middleware"

    # 可以不配置 __init__ 方法

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        print(">>> SimpleAbstractMiddleware called...")
        print("[SimpleAbstractMiddleware] → Request:", scope["path"])
        # 调用下一个 ASGI App
        await self.app(scope, receive, send)
        print("[SimpleAbstractMiddleware] ← Response sent")


# （3）基于 DefineMiddleware 实现中间件。
# 自定义Middleware时，如果需要在实例化时传入一些参数，可以借助此类。
# 注意，不是继承此类。
class SimpleInnerDefineMiddleware(AbstractMiddleware):
    """
    创建一个需要被 DefineMiddleware 封装的中间件，也需要继承 AbstractMiddleware
    """
    # 指定中间件的生效协议范围
    scopes = {ScopeType.HTTP}
    exclude = ["/somepath"]
    exclude_opt_key = "exclude_from_middleware"

    # __init__ 方法里有一些自定义参数需要配置
    def __init__(
            self,
            app: ASGIApp,
            exclude=None,
            exclude_opt_key=None,
            scopes=None,
            # ----- 自定义参数 ----
            custom: str | None = None
    ) -> None:
        super().__init__(app, exclude=exclude, exclude_opt_key=exclude_opt_key, scopes=scopes)
        # 这个自定义参数需要使用 DefineMiddleware 来封装传入
        self.custom = custom

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        print(">>> SimpleInnerDefineMiddleware called with custom: ", self.custom)
        # 调用下一个 ASGI App
        await self.app(scope, receive, send)


# ------------------------- 方式3 ----------------------------
# 基于 ASGIMiddleware 实现中间件
class SimpleASGIMiddleware(ASGIMiddleware):
    """
    ASGIMiddleware 做了更进一步的封装。
    使用时只需要注意两点：
    1. ASGIMiddleware 没有定义 __init__ 方法，所以用户需要自己定义 __init__ 方法，可以在其中执行任何操作
    2. ASGIMiddleware 只要求重写一个 handle 方法，并且该方法接受 4 个参数：在ASGI App 的三个参数基础上新增了一个 next_app 参数
    ASGIMiddleware.__call__ 方法只接受一个 ASGIApp 对象即可，它的内部会封装一个符合ASGI协议的函数。

    特别需要注意的是，ASGIMiddleware 在使用的时候，必须要传实例化后的对象，而不是像上面样传入类本身 ！！！
    """
    # 和 AbstractMiddleware 一样，也提供了下面三个配置
    scopes = (ScopeType.HTTP, ScopeType.ASGI)
    exclude_path_pattern: str | tuple[str, ...] | None = None
    exclude_opt_key: str | None = None

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        print(">>> SimpleASGIMiddleware called...")
        print("[SimpleASGIMiddleware] → Request:", scope["path"])
        # 调用下一个 ASGI App
        await next_app(scope, receive, send)
        print("[SimpleASGIMiddleware] ← Response sent")


# ------------------------- 自定义一些实用中间件 ----------------------------
class HTTPProcessTimeMiddleware(ASGIMiddleware):
    scopes = (ScopeType.HTTP, ScopeType.ASGI)

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        start_time = time.monotonic()

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                process_time = time.monotonic() - start_time
                headers = MutableScopeHeaders.from_message(message=message)
                headers["X-Process-Time"] = str(process_time)
                print("[HTTPProcessTimeMiddleware] → Response:", process_time)
            await send(message)

        await next_app(scope, receive, send_wrapper)
