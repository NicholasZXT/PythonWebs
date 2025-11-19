from typing import TYPE_CHECKING, AsyncGenerator, Annotated
from litestar import Router, Request, Response, HttpMethod, route, get, post
from litestar.enums import MediaType
from litestar.status_codes import HTTP_200_OK
from litestar.response import Stream
from litestar.serialization import encode_json
from litestar.background_tasks import BackgroundTask
from litestar.params import Parameter, Body
from litestar.openapi.spec.example import Example
from dataclasses import dataclass
from pydantic import BaseModel
from asyncio import sleep
from datetime import datetime

@dataclass
class SomeData:
    message: str
    data: dict


class AnotherData(BaseModel):
    message: str
    data: dict


class BodyData(BaseModel):
    # 使用 Parameter 或者 Body 来封装Post请求体的描述好像都可以
    # message: Annotated[str, Parameter(title="请求信息", description="请求信息message")]
    # data: Annotated[str, Parameter(title="提交数据", description="提交数据data")]
    message: Annotated[str, Body(title="请求信息", description="请求信息message")]
    data: Annotated[str, Body(title="提交数据", description="提交数据data")]


# route 装饰器是最基本的路由方式，get, post 都是它的快捷方式
@route(path="/", http_method=[HttpMethod.GET])
async def hello(request: Request) -> str:
    """
    简单视图函数
    :param request:
    :return:
    """
    request.logger.info(">>> Hello World for Function View")
    return "Hello Function View"


# ------------------ 展示路由装饰器的参数，大部分参数和 Litestar 对象接受的参数一样 ------------------
@get(
    path="/route_param",
    name="route_param",  # 为此视图函数命名
    operation_id="route_param",
    # ---- OpenAPI 配置 ----
    summary="路由装饰器参数(summary)",
    description="展示路由装饰参数的使用(description)",
    tags=["RouterParams"],
    include_in_schema=True,
    response_description="Response描述文本",
    # ---------------------
    media_type=MediaType.TEXT,
    status_code=HTTP_200_OK,
    dependencies=None,
    before_request=None,
    after_request=None,
    after_response=None,
    exception_handlers=None,
    middleware=None,
    # ---------------------
    # 使用 opt 参数，可以添加一些自定义属性
    opt={"some-key": "some-value"}
)
async def show_route_param(request: Request) -> str:
    """
    展示路由装饰器参数(function text)
    :param request:
    :return:
    """
    return "Show route params"


# ------------------ 展示返回的Response类型 ------------------
@get(
    path="/response/html",
    summary="返回HTML",
    description="返回HTML响应",
    media_type=MediaType.HTML,
    tags=["ResponseType"]
)
async def show_html_response(request: Request) -> str:
    return "<h1>HTML Response</h1>"

@get(
    path="/response/json/dict",
    summary="返回json",
    description="返回dict作为json响应",
    media_type=MediaType.JSON,
    tags=["ResponseType"]
)
async def show_json_response_with_dict(request: Request) -> dict:
    return {"message": "dict as json response"}

@get(
    path="/response/json/dataclass",
    summary="返回json",
    description="返回dataclass作为json响应",
    media_type=MediaType.JSON,
    tags=["ResponseType"]
)
async def show_json_response_with_dataclass(request: Request) -> SomeData:
    return SomeData(message="dataclass as json response", data={"key": "value"})

@get(
    path="/response/json/pydantic",
    summary="返回json",
    description="返回pydantic模型作为json响应",
    media_type=MediaType.JSON,
    tags=["ResponseType"]
)
async def show_json_response_with_pydantic(request: Request) -> AnotherData:
    return AnotherData(message="pydantic model as json response", data={"key": "value"})


async def stream_generator(cnt: int = 5) -> AsyncGenerator[bytes, None]:
    count = 1
    while True:
        yield encode_json({"current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        count += 1
        if count >= cnt:
            break
        await sleep(0.5)

@get(
    path="/response/stream",
    summary="Stream Response",
    description="返回流式响应",
    # media_type=MediaType.JSON,
    tags=["ResponseType"]
)
async def show_stream_response(request: Request) -> Stream:
    return Stream(stream_generator())


# ------------------ 后台任务 ------------------
async def logging_task(logger, identifier: str, message: str) -> None:
    logger.info("%s: %s", identifier, message)

@get(
    path="/background_task",
    summary="Background Task",
    description="后台任务",
    # media_type=MediaType.TEXT,
    tags=["BackgroundTask"],
    sync_to_thread=False
)
def show_background_task(request: Request, name: str) -> Response[dict[str, str]]:
    # return "Background Task"
    return Response(
            {"hello": name},
            background=BackgroundTask(logging_task, logger=request.logger, identifier="greeter", message=f"was called with name {name}"),
        )

# ------------------ 请求参数解析 ------------------
@get(
    path="/params/path/{version:int}",
    summary="Parameter Path",
    description="Path参数解析",
    media_type=MediaType.JSON,
    tags=["RequestParam"]
)
async def show_param_path(
        request: Request,
        # 可以使用 Annotated 来添加参数的描述信息
        version: Annotated[
            int,
            Parameter(
                title="版本号",
                description="Get a specific version spec from the available specs",
                ge=1,
                le=10,
                examples=[Example(value=2)]
            )
        ],
) -> dict:
    return {"message": "Path Parameter", "version": version}


@get(
    path="/params/query",
    summary="Parameter Query",
    description="Query参数解析，直接在视图函数中定义关键字即可",
    media_type=MediaType.JSON,
    tags=["RequestParam"]
)
async def show_param_query(
        request: Request,
        name: Annotated[
            str,
            Parameter(
                title="名称",
                description="必选参数",
                examples=[Example(value="Litestar")]
            )
        ],
        version: Annotated[
            int,
            Parameter(
                title="版本号",
                description="版本号，默认值为1",
                ge=1,
                le=10,
                examples=[Example(value=2)]
            )
        ] = 1,
        desc: Annotated[
            str | None,
            Parameter(
                title="描述",
                description="描述文本，可选参数",
                examples=[Example(value="Litestar is a modern Python web framework")]
            )
        ] = None,
) -> dict:
    return {"message": "Path Parameter", "name": name, "version": version, "desc": desc}


@post(
    path="/params/body",
    summary="Parameter Body",
    description="Post请求Body参数解析,参数直接使用Pydantic模型即可",
    media_type=MediaType.JSON,
    tags=["RequestParam"]
)
async def show_param_body(
        request: Request,
        # data: BodyData
        # 也可以配合 Annotated 添加参数描述信息
        data: Annotated[BodyData, Body(title="Body参数", description="Body参数", examples=[Example(value={"message": "Litestar", "data": "some data"})])]
) -> BodyData:
    return data


@post(
    path="/params/mix/{version:int}",
    summary="Parameter Mix",
    description="混合参数解析",
    media_type=MediaType.JSON,
    tags=["RequestParam"]
)
async def show_param_mix(
        request: Request,
        version: Annotated[int, Parameter(title="版本号", description="版本号", ge=1, le=10)],
        name: Annotated[str, Parameter(title="名称", description="名称必选参数")],
        data: Annotated[BodyData, Body(title="Body参数", description="Body参数", examples=[Example(value={"message": "Litestar", "data": "some data"})])]
) -> dict:
    request.logger.info("[show_param_mix] Mix Parameter Parsing...")
    return {"message": "Mix Parameter", "name": name, "version": version, "data": data}


# ----------------------------------------------------
api_router = Router(
    path="/router",
    tags=["FunctionView"],
    route_handlers=[
        hello,
        show_route_param,
        show_html_response,
        show_json_response_with_dict,
        show_json_response_with_dataclass,
        show_json_response_with_pydantic,
        show_stream_response,
        show_background_task,
        show_param_path,
        show_param_query,
        show_param_body,
        show_param_mix
    ]
)
