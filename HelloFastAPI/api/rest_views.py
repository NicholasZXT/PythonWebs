"""
展示 fastapi-utils 插件使用
"""
from fastapi import APIRouter, Path, Query, Body, Request, status, Depends
from fastapi.responses import Response, JSONResponse, PlainTextResponse, HTMLResponse
from fastapi_restful.cbv import cbv
from fastapi_restful import Resource, Api, set_responses
# from fastapi_restful.api_model import APIMessage, APIModel


# ------------- 第1种 CBV 使用方式 -------------
# 这种方式用起来比较顺手
rest_router = APIRouter(
    prefix='/rest',
    tags=['API-Restful']
)

def some_dependency():
    s = "some_dependency"
    print(s)
    return s


@cbv(router=rest_router)
class RestfulApi:
    # 所有视图函数中都需要的依赖可以采用类属性的方式
    some: str = Depends(some_dependency)

    # 下面视图函数中的 self 参数不会显示在 swagger 文档中，这一点很好，比 fastapi-router-controller 考虑的周全
    @rest_router.get(
        path="/",
        name="Hello RestfulApi",
        summary="Hello RestfulApi",
        response_class=JSONResponse
    )
    def hello_rest(self):
        return {"message": "Hello for FastAPI-utils"}

    @rest_router.get(
        path="/some_dep",
        name="Some Depends",
        summary="Some Depends",
        response_class=JSONResponse
    )
    def some_dep(self):
        # 可以通过如下方式访问类属性得到的依赖注入
        return {"message": self.some}


# ------------- 第2种 CBV 使用方式 -------------
# 继承Resource类，后续在FastAPI实例中，使用如下方式注册
# 感觉这种方式侵入性比较大，并且不能对自动生成的 ApiRouter 进行配置（单个视图函数的文档好像也不能配置）—— 不好用
# from fastapi_restful import Api
# api = Api(app)
# my_resource = MyResource()
# api.add_resource(my_resource, "/rest/resource")

# 查看源码会发现，这个Resource类只是个空壳子，重要的逻辑在 Api 类里面，并且底层也是对上面第1种方式做的封装
class MyResource(Resource):
    def get(self):
        return {"message": "Get Response"}

    def put(self):
        return {"message": "Put Response"}

    def post(self):
        return {"message": "Post Response"}

    def delete(self):
        return {"message": "Delete Response"}



