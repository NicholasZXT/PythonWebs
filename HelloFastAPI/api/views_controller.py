"""
展示fastapi-router-controller插件使用。
结论：不好用，不推荐
"""
from fastapi import APIRouter, Path, Query, Body, Request, status, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi_router_controller import Controller

controller_router = APIRouter(
    prefix='/controller',
    tags=['API-Controller']
)
controller = Controller(controller_router)

def class_dependency():
    s = "class_dependency"
    print(s)
    return s

def init_dependency():
    s = "init_dependency"
    print(s)
    return s

@controller.resource()
class ControllerRouter:

    # 设置类级别的依赖
    # add class wide dependencies e.g. auth
    dependencies = [Depends(class_dependency)]

    # 初始化时可以设置一些依赖，以便在下面的 controller 视图中使用
    # you can define in the Controller init some FastApi Dependency and them are automatically loaded in controller methods
    def __init__(self, x: str = Depends(init_dependency)):
        self.x = x

    # 下面视图函数中的 self 参数会被显示在文档界面，有问题 -------------- KEY
    @controller.route.get("/", summary="Here is summary for controller.", response_class=JSONResponse)
    def hello_controller(self):
        return {"message": "Hello for fast-api-controller"}

    @controller.route.get("/some", response_class=JSONResponse)
    def some(self):
        print(self.x)
        return {"message": self.x}
