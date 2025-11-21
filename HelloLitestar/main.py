from contextlib import asynccontextmanager
from typing import AsyncGenerator
from litestar import Litestar, get, Request, Response, MediaType
from litestar.config.app import AppConfig
from litestar.logging import LoggingConfig
from litestar.di import Provide
from litestar.openapi import OpenAPIConfig
from litestar.openapi.spec import Contact, License, Tag
from litestar.datastructures import State
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from config import get_settings, settings
from api import api_router, MyController, UserController, DependencyController
from auth import jwt_auth, AuthController


logging_config = LoggingConfig(
    root={"level": "INFO", "handlers": ["queue_listener"]},
    # root={"level": "DEBUG", "handlers": ["queue_listener"]},
    formatters={
        "standard": {
            # "format": "[%(asctime)s][%(levelname)s][%(name)s] %(message)s",
            "format": "[%(asctime)s][%(levelname)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    log_exceptions="always",
)

@get("/")
async def hello(request: Request) -> str:
    """
    Hello World for Litestar.
    """
    request.logger.info(f">>> Hello World for Litestar")
    hello_str = "Hello Litestar !"
    return hello_str


# 对于非阻塞的同步函数，可以设置 sync_to_thread=False；对于阻塞的同步函数，需要设置 sync_to_thread=True，放到单独的线程池执行
@get("/exception", sync_to_thread=False)
def some_exception() -> None:
    """Route handler that raises an exception."""
    raise HTTPException(detail="bad request", status_code=HTTP_400_BAD_REQUEST)


def app_init(config: AppConfig) -> AppConfig:
    """
    这里可以对 AppConfig 做一些修改操作
    :param config:
    :return:
    """
    print(">>> app_init called...")
    return config


def startup_hook(app: Litestar) -> None:
    app.logger.info(f">>> startup_hook called...")


def shutdown_hook(app: Litestar) -> None:
    app.logger.info(f">>> shutdown_hook called...")


@asynccontextmanager
async def lifespan_hook(app: Litestar) -> AsyncGenerator[str, None]:
    app.logger.info(f">>> lifespan_hook called...")
    try:
        app.logger.info(f">>> lifespan_hook yield something...")
        yield "something"
    except Exception as e:
        app.logger.error(f">>> lifespan_hook error: {e}")
    finally:
        app.logger.info(f">>> lifespan_hook finally do some cleaning.")


async def before_request_handler(request: Request) -> dict[str, str] | None:
    request.app.logger.info(f">>> before_request_handler called...")
    return None

# async def after_request_handler(app: Litestar) -> Litestar:
#     app.logger.info(">>> after_request_handler called...")
#     return app
# 或者下面这种
async def after_request_handler(response: Response) -> Response:
    print(">>> after_request_handler called...")
    return response

async def after_response_handler(request: Request) -> None:
    request.app.logger.info(f">>> after_response_handler called...")

async def after_exception_handler(exc: Exception, scope: "Scope") -> None:
    """Hook function that will be invoked after each exception."""
    app = Litestar.from_scope(scope)
    state = app.state
    if not hasattr(state, "error_count"):
        state.error_count = 1
    else:
        state.error_count += 1

    app.logger.warning(
        "[after_exception_handler] an exception of type %s has occurred for requested path %s and the application error count is %d.",
        type(exc).__name__,
        scope["path"],
        state.error_count,
    )


def plain_text_exception_handler(request: Request, exc: Exception) -> Response:
    """Default handler for exceptions subclassed from HTTPException."""
    app = request.app
    app.logger.warning("[plain_text_exception_handler] an exception of type %s has occurred for requested path %s.", type(exc).__name__, request.url)
    status_code = getattr(exc, "status_code", HTTP_500_INTERNAL_SERVER_ERROR)
    detail = getattr(exc, "detail", "")
    return Response(
        media_type=MediaType.TEXT,
        content=detail,
        status_code=status_code,
    )


app = Litestar(
    # 最重要的参数：路由处理器，可以是 Router | Controller | HTTPRouteHandler | WebsocketRouteHandler | ASGIRouteHandler
    route_handlers=[
        hello, some_exception,
        api_router,
        MyController,
        UserController,
        DependencyController,
        AuthController
    ],
    # debug模式，True 时会将错误信息渲染为HTML返回
    debug=settings.debug,
    # 全局依赖注入
    dependencies={
        # 这里将配置信息作为全局依赖注入
        # get_settings 虽然是同步函数，但确定不会阻塞，所以设置 sync_to_thread=False，否则会抛出warning
        "app_settings": Provide(get_settings, sync_to_thread=False)
    },
    logging_config=logging_config,
    dto=None,
    return_dto=None,
    state=None,
    # ------ 启动和关闭回调 ------
    on_startup=[startup_hook],
    on_shutdown=[shutdown_hook],
    on_app_init=[
        app_init,
        # 注册 jwt_auth 的初始化操作
        jwt_auth.on_app_init
    ],
    lifespan=[lifespan_hook],
    # ------ 请求处理hook ------
    before_request=before_request_handler,
    after_response=after_response_handler,
    after_request=after_request_handler,
    before_send=None,
    after_exception=[after_exception_handler],
    # ------ 全局异常处理器 ------
    exception_handlers={HTTPException: plain_text_exception_handler},
    # ------ 中间件 ------
    middleware=None,
    cors_config=None,
    csrf_config=None,
    # --------------- OpenAPI 配置 ---------------
    # 全局标签，一般用的不多
    tags=["HelloLitestar"],
    # 是否在OpenAPI schema中显示
    include_in_schema=True,
    # OpenAPI 配置
    # openapi_config=None,   # 设为None表示关闭OpenAPI文档
    openapi_config=OpenAPIConfig(
        title="HelloLitestar",
        version="1.0.0",
        description="Hello Litestar Demo",
        summary="Hello Litestar Demo",
        tags=[
            Tag(name="HelloLitestar", description="Hello Litestar Demo")
        ],
        # OpenAPI 的根路径，默认为 /schema
        path="/schema",
        # OpenAPI 文档的站点，默认为None
        root_schema_site="swagger",
        contact=Contact(
            name="HelloLitestar",
            url="litestar@github.com",
            email="litestar@github.com",
        ),
        license=License(name="MIT", url="https://github.com/litestar-org/litestar/blob/main/LICENSE")
    )
)
# 也可以使用下面的方式创建App
# app = Litestar.from_config(AppConfig())

# 也可以使用下面的方式注册路由处理器
# app.register()

# 日志使用
app.logger.info(f"Starting {settings.app_name}")

# 执行：
# 方式1：uvicorn main:app --reload
# 方式2，使用Litestar CLI: litestar --app=main:app run --host=localhost --port=8100 --reload
# OpenAPI 访问地址如下：
# http://localhost:8100/schema (for ReDoc),
# http://localhost:8100/schema/swagger (for Swagger UI),
# http://localhost:8100/schema/elements (for Stoplight Elements)
# http://localhost:8100/schema/rapidoc (for RapiDoc)
