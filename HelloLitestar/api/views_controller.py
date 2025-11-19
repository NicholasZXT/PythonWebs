from typing import TYPE_CHECKING
from uuid import UUID, uuid4
from litestar import Controller, Request, Response, get, post, put, delete, MediaType
from litestar.di import Provide
from litestar.params import Dependency
from config import AppSettings
from .models import User, UserReadDTO, UserWriteDTO


class MyController(Controller):
    """
    Controller路由视图。
    router 的参数都变成了这里的类实例变量
    """
    path = '/controller'

    @get("/")
    async def hello(self, request: Request) -> str:
        request.logger.info(f">>> Hello World for Controller View")
        return "<h1>Hello Controller View</h1>"


class UserController(Controller):
    """
    Controller 配合 DTO 实现 CRUD 的多种数据视图配置
    """
    tags = ["UserDTO"]
    path = '/user'
    dto = UserWriteDTO
    return_dto = UserReadDTO

    @post("/", sync_to_thread=False)
    def create_user(self, data: User) -> User:
        return data

    @get("/", sync_to_thread=False)
    def get_users(self) -> list[User]:
        return [User(name="Mr Sunglass", email="mr.sunglass@example.com", age=30)]

    @get("/{user_id:uuid}", sync_to_thread=False)
    def get_user(self, user_id: UUID) -> User:
        return User(uid=user_id, name="Mr Sunglass", email="mr.sunglass@example.com", age=30, passwd_hash="<PASSWORD>")

    @put("/{user_id:uuid}", sync_to_thread=False)
    def update_user(self, data: User) -> User:
        return data

    @delete("/{user_id:uuid}", return_dto=None, sync_to_thread=False, status_code=200)
    def delete_user(self, user_id: UUID) -> dict:
        return {"message": f"User [{user_id}] deleted"}


def controller_dependency(request: Request) -> str:
    request.logger.info(f">>> controller_dependency called from request: {request.url}")
    return "controller_dependency_value"

def local_dependency(request: Request) -> str:
    request.logger.info(f">>> local_dependency called from request: {request.url}")
    return "local_dependency_value"


class DependencyController(Controller):
    """
    展示 Litestar 里依赖注入系统的使用。
    """
    path = "/dependency"
    tags = ['Dependency']

    # 定义Controller基本的依赖
    dependencies = {
        "controller_dep": Provide(controller_dependency, sync_to_thread=False)
    }

    @get(
        path="/",
        sync_to_thread=False,
        dependencies={
            "local_dep": Provide(local_dependency, sync_to_thread=False)
        },
        summary="依赖注入基本使用",
        description="展示 Litestar 里依赖注入系统的使用",
        media_type=MediaType.JSON
    )
    def show_dependency(
            self,
            # 这个 key 来源于全局依赖注入的 key
            app_settings: AppSettings,
            controller_dep: str,
            local_dep: str,
    ) -> dict:
        data = {"app_settings": app_settings.dict(), "controller_dep": controller_dep, "local_dep": local_dep}
        return data

