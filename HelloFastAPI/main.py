import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app1 import user_router
from app_auth import auth_router
from dependencies.database_dep import create_db_tables

# 用于自定义描述 一组 接口的文档，是一个 list of dict，每个dict必须有两个key：name 是 @app.get() 中的 tags= 参数的值，description 是描述
# 这里的 tags 是用于对接口进行分组，而不是具体到每个端点的文档描述
# 每个路由端点的文档描述，只需要在路由函数的docstring里写好，就会自动显示在 Swagger UI 和 ReDoc 上
tags_metadata = [
    {"name": "Hello", "description": "Hello World APIs in FastAPI"},
    {"name": "User-App", "description": "User App 接口"},
    {"name": "Auth-App", "description": "Auth App 接口"}
]

app = FastAPI(
    title="FastAPI Demos",
    description="Description: Show how to use FastAPI.",
    summary="Summary: Here is summary...",
    version="1.0.0",
    openapi_tags=tags_metadata,
    docs_url="/docs",   # Swagger UI 文档的URL，None 表示禁用
    redoc_url="/redoc"  # ReDoc 文档的 URL，None 表示禁用
)

create_db_tables()
app.include_router(user_router, prefix="/user_app")
app.include_router(auth_router, prefix="/auth_app")

@app.get(path='/', response_class=HTMLResponse, tags=['Hello'])
def hello():
    # 视图函数的 docstring 会显示在 Swagger UI 文档里每个接口下面
    """
    Hello World for FastAPI.
    """
    hello_str = "<h1>Hello FastAPI !</h1>"
    return HTMLResponse(content=hello_str)

if __name__ == "__main__":
    port = 8100
    uvicorn.run("main:app", port=port, log_level="info")
