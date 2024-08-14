import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from api import api_router
from user_app import user_router
from auth_app import auth_router

app = FastAPI(
    debug=False,  # 调试参数
    # ----- 以下为 API交互式文档的配置参数 -----
    title="FastAPI Demos",
    version="1.0.0",
    summary="Here is summary...",
    description="Here is description: Show how to use FastAPI.",
    docs_url="/docs",    # SwaggerUI文档的URL，默认为 /docs, None 表示禁用
    redoc_url="/redoc",  # ReDoc文档的URL，默认为 /redoc, None 表示禁用
    openapi_prefix='',            # 配置访问 openapi_json.json 文件路径的前缀，默认空字符串
    openapi_url="/openapi.json",  # 配置访问 openapi_json.json 文件路径，此处为默认值
    openapi_tags=[  # 配置接口分组的描述信息
        # 用于自定义描述 一组 接口的文档，是一个list of dict，每个dict必须有两个key:
        # name 是@app.get()中 tags= 参数值; description 是该组接口的描述
        # 这里的 tags 是用于对接口进行分组，而不是具体到每个端点的文档描述
        # 每个路由端点的文档描述，只需要在路由视图函数的docstring里写好，就会自动显示在 Swagger UI 和 ReDoc 上
        {"name": "Hello", "description": "Hello World APIs in FastAPI"},
        {"name": "API-App", "description": "APIs"},
        {"name": "User-App", "description": "User App"},
        {"name": "Auth-App", "description": "Auth App"}
    ],
    license_info={   # 配置API公开的许可证信息
        "name": "License info is here",
        "url": "https://license.example.com"
    },
    contact={  # 联系人信息
        "name": "Contact Me",
        "url": "https://author.example.com",
        "email": "example@gmail.com"
    }
)

@app.get(path='/', response_class=HTMLResponse, tags=['Hello'])
def hello():
    # 视图函数的 docstring 会显示在 Swagger UI 文档里每个接口下面
    """
    Hello World for FastAPI.
    """
    hello_str = "<h1>Hello FastAPI !</h1>"
    return HTMLResponse(content=hello_str)

app.include_router(api_router, prefix="/api")
app.include_router(user_router, prefix="/user_app")
app.include_router(auth_router, prefix="/auth_app")


if __name__ == "__main__":
    from dependencies.database_dep import init_db_tables
    init_db_tables()
    # 使用 uvicorn 运行 FastAPI 应用，可以参考 uvicorn 官网文档 https://www.uvicorn.org/#quickstart
    port = 8100
    # 第一种方式，其中的 main 对应的是 main.py 的文件名，不带后缀
    uvicorn.run("main:app", port=port, log_level="info")
    # 第二种方式
    # config = uvicorn.Config("main:app", port=port, log_level="info")
    # server = uvicorn.Server(config)
    # server.run()
