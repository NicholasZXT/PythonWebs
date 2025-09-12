import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import init_db_tables
from user_app import user_router
from auth_app import custom_jwt_router, login_router, authx_router
from api import api_router, rest_router, MyResource, streaming_router, file_router, batch_router
# from api import controller

app = FastAPI(
    debug=settings.DEBUG,  # 调试参数
    # ----- 以下为 API交互式文档的配置参数 -----
    title="FastAPI Demos",
    version="1.0.0",
    summary="Here is summary...",
    description="Here is description: Show how to use FastAPI.",
    # SwaggerUI文档的URL，默认为 /docs, None 表示禁用
    docs_url="/docs" if settings.SWAGGER_UI_ENABLE else None,
    redoc_url="/redoc",  # ReDoc文档的URL，默认为 /redoc, None 表示禁用
    openapi_prefix='',            # 配置访问 openapi_json.json 文件路径的前缀，默认空字符串
    openapi_url="/openapi.json",  # 配置访问 openapi_json.json 文件路径，此处为默认值
    openapi_tags=[  # 配置接口分组的描述信息
        # 用于自定义描述 一组 接口的文档，是一个list of dict，每个dict必须有两个key:
        # name 是@app.get()中 tags= 参数值; description 是该组接口的描述；即使该 tag 下没有路由，也会显示在文档页面上
        # 这里的 tags 是用于对接口进行分组，而不是具体到每个端点的文档描述
        # 每个路由端点的文档描述，只需要在路由视图函数的docstring里写好，就会自动显示在 Swagger UI 和 ReDoc 上
        {"name": "Hello", "description": "Hello World for FastAPI"},
        {"name": "API-App", "description": "展示 FastAPI 请求/响应的基本使用"},
        {"name": "User-App", "description": "展示 FastAPI 的数据库使用"},
        {"name": "Auth-App-Custom-JWT", "description": "展示 FastAPI 使用 Password-Bearer + 自定义JWT验证 实现令牌认证"},
        {"name": "FileUpload-App", "description": "文件上传接口"}
    ],
    include_in_schema=True,
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

# -------- CORS配置 --------
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化数据库可以采用如下方式
# @app.on_event("startup")
# def init_db():
#     # 需要提前导入要初始化的表，否则可能未注册到 metadata 里
#     from user_app.models import User
#     init_db_tables()


@app.get(path='/', response_class=HTMLResponse, tags=['Hello'])
def hello_fastapi():
    # 视图函数的 docstring 会显示在 Swagger UI 文档里每个接口下面
    """
    Hello World for FastAPI.
    """
    hello_str = "<h1>Hello FastAPI !</h1>"
    return HTMLResponse(content=hello_str)


# 这里引入时使用的 prefix 会和实例化 APIRouter 时的 prefix 指定的前缀拼在一起，并且此处设置的 prefix 在前面
app.include_router(api_router)
# # app.include_router(api_router, prefix="/api_prefix")
app.include_router(user_router)
# 流式响应接口
app.include_router(streaming_router)
# 文件上传接口
app.include_router(file_router)
# 异步批量处理演示接口
app.include_router(batch_router)

# JWT认证相关Router
# 注意，custom_jwt_router 和 login_router 里都设置了一个 OAuth2PasswordBearer，那么在 SwaggerUI 界面的 Authorize 里会显示两个登录验证的地方
# 如果下面没有 include_router，那么 SwaggerUI 界面的 Authorize 里就不显示对应的登录验证框
app.include_router(custom_jwt_router)
# FastAPI-Login视图
app.include_router(login_router)
# AuthX 视图
# AuthX的一个问题是，它没有继承 fastapi.security 里的 OAuth2PasswordBearer 等类，所以默认情况下无法在 SwaggerUI 界面显示 Authorize 按钮
app.include_router(authx_router)

# FastAPI-Auth-JWT使用，它需要以中间件的方式注册，这一点不太好 —— 不推荐
# from fastapi_auth_jwt import JWTAuthenticationMiddleware
# from auth_app.dependencies import auth_backend
# app.add_middleware(
#     middleware_class=JWTAuthenticationMiddleware,
#     backend=auth_backend,
#     exclude_urls=["/auth_app/auth_jwt/login", "/auth_app/auth_jwt/sign-up"],  # Public endpoints
# )
# from auth_app.auth_jwt_views import auth_jwt_router
# app.include_router(auth_jwt_router)

# fastapi-utils的CBV使用
# --- 第1种方式，用起来不错
app.include_router(rest_router)
# --- 第2种方式，不好用，不推荐
# from fastapi_restful import Api
# api = Api(app)
# my_resource = MyResource()
# api.add_resource(my_resource, "/rest/resource")

# fastapi-router-controller插件提供的CBV并不好用
# app.include_router(controller.router)


if __name__ == "__main__":
    # from database import init_db_tables
    # init_db_tables()
    # 使用 uvicorn 运行 FastAPI 应用，可以参考 uvicorn 官网文档 https://www.uvicorn.org/#quickstart
    host = "localhost"
    # host = "10.8.6.203"
    port = 8100
    # 第一种方式，其中的 main 对应的是 main.py 的文件名，不带后缀
    uvicorn.run("main:app", host=host, port=port, log_level="info")
    # 第二种方式
    config = uvicorn.Config("main:app", host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    server.run()
