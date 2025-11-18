from litestar import Litestar, get
from litestar.di import Provide
from config import get_settings, settings


@get("/")
async def hello() -> str:
    return "Hello, world!"

app = Litestar(
    route_handlers=[hello],
    debug=settings.debug,
    # 可通过 DI 注入 settings 到路由处理器
    dependencies={
        # get_settings 虽然是同步函数，这里确定不会阻塞，所以设置 sync_to_thread=False，否则会抛出warning
        "settings": Provide(get_settings, sync_to_thread=False)
    },
)
# 执行：
# 方式1：uvicorn main:app --reload
# 方式2，使用Litestar CLI: litestar --app=main:app run --host=localhost --port=8100 --reload
# OpenAPI 访问地址如下：
# http://localhost:8100/schema (for ReDoc),
# http://localhost:8100/schema/swagger (for Swagger UI),
# http://localhost:8100/schema/elements (for Stoplight Elements)
# http://localhost:8100/schema/rapidoc (for RapiDoc)
