"""
Litestar 提供了 Controller 类来封装一组视图函数。
Controller 和 Java Web 里 Spring 框架提供的 @Controller 注解标识的类很相似。

这里还展示了如下内容：
- Litestar 内置的DTO支持
"""
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

