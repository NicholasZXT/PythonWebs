"""
练习FastAPI视图函数/路由的如何获取请求信息，以及返回响应报文
"""
from typing import Union
from pydantic import BaseModel
from fastapi import APIRouter, Path, Query, Body, Request, status
from fastapi.responses import Response, JSONResponse, PlainTextResponse, HTMLResponse
from fastapi.encoders import jsonable_encoder
from enum import Enum
from .schemas import ItemBody, UserBody

api_router = APIRouter(tags=['API-App'])


# 路由装饰器的通用参数（和get,post,put无关）如下
@api_router.get(
    path='/hello',
    # --- API文档相关参数 ---
    tags=['Hello'],
    name='api-hello',  # 设置API文档中该路由接口的名称，和下面的summary类似，会优先显示summary，主要是用于反向查询
    summary='Hello summary for API',  # 设置 API 文档中该路由接口的名称，默认值为当前被装饰函数的名称
    # description='Hello description for API.',  # 设置 API 文档中对该路由功能的详细描述，支持Markdown，它会覆盖视图函数的 docstring ！
    response_description='Hello response description for API',  # 设置 API 文档中对该路由响应报文信息结果的描述
    include_in_schema=True,   # 设置此路由接口信息是否在API文档中显示
    # --- 与响应报文相关参数 ---
    # status_code=status.HTTP_200_OK,
    # responses={status.HTTP_200_OK: {'ok': 'SomeClass'}},  # 设置不同状态码对应的响应模型
    # response_class=JSONResponse,     # 设置响应报文使用的Response类，默认是JSON
    # response_model=None,  # 定义函数处理结果中返回的 JSON 的模型类，会将输出数据转换为对应的 response_model 中声明的数据模型
    # response_model_exclude={'field1', 'field2'},  # 设置响应模型的JSON中排除哪些字段
    # response_model_include={'field3', 'field4'},  # 设置响应模型的JSON中包含哪些字段
    # --- 其他参数 ---
    # dependencies=[]  # 依赖注入项目
)
async def hello_api():
    """
    Hello api docstring...
    """
    hello_str = "<h1>Hello API !</h1>"
    return HTMLResponse(content=hello_str)


# ------------------- 展示路由视图函数的 路径参数（Path）获取 -------------------
@api_router.get(path="/user/{user_name}/item/{item_id}", tags=['API-Path'], summary='路径参数获取')
def get_item(user_name: str, item_id: int):
    return {'user_name': user_name, 'item_id': item_id}


class ItemCategory(str, Enum):
    c1 = 'category-1'
    c2 = 'category-2'
    c3 = 'category-3'

@api_router.get(path="/item/category/{cate_name}", tags=['API-Path'], summary='路径参数枚举值')
def get_item_category(cate_name: ItemCategory):
    """
    cate_name 为枚举值.
    """
    return {'category': cate_name.name}


@api_router.get(path="/item/{item_id}", tags=['API-Path'], summary='路径参数校验')
def get_item_check(item_id: int = Path(title='ItemID', description='Item标识符', gt=0.0, lt=100)):
    """
    item_id 使用 Path() 校验，但是校验条件不会显示在 API 文档里.
    """
    # 注意，Path() 里不能使用 default，因为路径参数都是必须的
    return {'item_id': item_id}


# ------------------- 展示路由视图函数的 查询参数（Query）获取 -------------------
@api_router.get(path="/items/scoll", tags=['API-Query'], summary='查询参数获取')
def get_query_param(page: int, limit: int, info: str = 'default_info'):
    # page 和 limit 都是必填参数
    return {'page': page, 'limit': limit, 'info': info}

@api_router.get(path="/items/check", tags=['API-Query'], summary='查询参数校验')
def get_query_param_check(
        page: int = Query(default=None, ge=1, le=20),
        limit: int = Query(default=None, ge=1, le=100),
        info: str = Query(default='default_info', min_length=1, max_length=30)
):
    """
    查询参数使用 Query() 校验，校验条件会显示在 API 文档上.
    """
    # page 和 limit 都是必填参数
    return {'page': page, 'limit': limit, 'info': info}


# ------------------- 展示路由视图函数的 请求体参数（Body）获取 -------------------
@api_router.post(path="/body/item", tags=['API-Body'], summary='请求体参数获取')
def get_body_item(item: ItemBody):
    return {
        'item_id': item.id,
        'item_name': item.name,
        'item_used': item.used
    }

@api_router.post(path="/body/user", tags=['API-Body'], summary='请求体参数获取')
def get_body_user(user: UserBody):
    return {
        'user_id': user.uid,
        'user_name': user.name,
        'user_age': user.age,
        'user_gender': user.gender
    }

@api_router.post(path="/body/multiple", tags=['API-Body'], summary='多个请求体参数')
def get_body_param_multiple(item: ItemBody, user: UserBody):
    return {'item': item, 'user': user}

@api_router.post(path="/body/single", tags=['API-Body'], summary='单值请求参数')
def get_body_param_single(
    item: ItemBody,
    user_name: str = Body(default=None, min_length=1, max_length=20, title='用户名称')  # 单值请求参数，注意它在请求体中的要求
):
    return {
        'item': item,
        'user_name': user_name
    }


# ------------------- 展示路由视图函数的 混合参数 获取 -------------------
# 总结下来，视图函数中的参数对应规则如下：
# 1. URL路径中有同名参数，则识别为 Path 参数；
# 2. 参数为 Pydantic 的Model 类 且方法为POST，识别为 Body 参数；
# 3. 上述两者都不是，识别为 Query 参数
@api_router.post(path="/param/mix/{item_id}", tags=['API-App'], summary='混合参数获取')
def get_param_mix(
    item: ItemBody,
    item_id: int = Path(ge=0),
    page: int = Query(default=1, ge=1, le=20),
    user_name: str = Body(default='', min_length=1, max_length=30)
):
    return {
        'item_id': item_id,
        'page': page,
        'user_name': user_name,
        'item': item
    }


# ------------------- 展示路由视图函数的 请求报文 获取 -------------------
@api_router.post("/req/data/{page}", tags=['API-Request'], response_class=JSONResponse)
async def get_request_data(request: Request, item: ItemBody, page: int, limit: int):  # 视图函数中显式声明 Request 参数后，就可以获取请求对象
    """获取请求信息"""
    # 下面这 3 个方法都是协程方法，所以只能在异步视图函数中使用
    form_data = await request.form()
    json_data = await request.json()
    body_data = await request.body()
    return {
        # request.url 是一个 URL 对象，封装了一些属性
        'request.url.scheme': request.url.scheme,
        'request.url.port': request.url.port,
        'request.url.path': request.url.path,
        'request.base_url': request.base_url,
        'request.method': request.method,
        'request.path_params': request.path_params,
        'request.query_params': request.query_params,
        'request.form()': form_data,
        'request.body()': body_data,
        'request.json()': json_data,
    }


# ------------------- 展示路由视图函数的 响应报文 返回 -------------------
@api_router.get("/res/default1", tags=['API-Response'])
def get_response_default1():
    """默认响应报文就是JSON"""
    return {"Hello": "World"}

@api_router.get("/res/default2", tags=['API-Response'])
def get_response_default2():
    """HTML字符串默认也会被作为JSON处理"""
    # 字符串也会被转成JSON
    return "<h1>Hello FastAPI !</h1>"

@api_router.get("/res/json", tags=['API-Response'])
def get_response_json():
    """指定返回JSON"""
    # 完整写法
    data = {"Hello": "World"}
    json_compatible_item_data = jsonable_encoder(data)
    return JSONResponse(content=json_compatible_item_data)

@api_router.get("/res/plaintext", tags=['API-Response'], response_class=PlainTextResponse)
def get_response_text():
    """返回纯文本"""
    html = "<h1>Hello FastAPI !</h1>"
    # return Response(content=html, media_type="text/plain")
    return PlainTextResponse(content=html)

@api_router.get("/res/html", tags=['API-Response'], response_class=HTMLResponse)
def get_response_html():
    """返回HTML"""
    html = "<h1>Hello FastAPI !</h1>"
    return HTMLResponse(content=html)

@api_router.get("/res/model", tags=['API-Response'], response_class=JSONResponse, response_model=UserBody)
def get_response_model():
    """返回Pydantic模型"""
    user = UserBody(uid=1, name='Someone', age=30, gender='male')
    return user
