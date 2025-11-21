"""
Litestar 提供的认证机制也是采用中间件形式来实现的。
"""
from litestar.enums import ScopeType
from litestar.types import ASGIApp, Message, Receive, Scope, Send
from litestar.datastructures import MutableScopeHeaders
from litestar.connection import ASGIConnection, Request
from litestar.handlers import BaseRouteHandler
from litestar.middleware import AbstractAuthenticationMiddleware, AuthenticationResult
from litestar.security import AbstractSecurityConfig
from litestar.security.jwt import Token, JWTAuth, JWTCookieAuth, OAuth2PasswordBearerAuth
from litestar.security.session_auth import SessionAuth
from litestar.exceptions import HTTPException, NotAuthorizedException
from litestar.openapi import OpenAPIConfig

from .models import MockToken, MockUser, User


# ----------------------- 自定义认证中间件实现 ---------------------
class CustomAuthenticationMiddleware(AbstractAuthenticationMiddleware):
    API_KEY_HEADER = "Bear"
    TOKEN_USER_DATABASE = {
        "XiaoMing": ("XiaoMing", "20", "admin"),
        "XiaoHong": ("XiaoHong", "18", "normal")
    }

    async def authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult:
        """
        Given a request, parse the request api key stored in the header
        and retrieve the user correlating to the token from the DB
        """
        # retrieve the auth header
        auth_header = connection.headers.get(self.API_KEY_HEADER)
        if not auth_header:
            raise NotAuthorizedException()

        # this would be a database call
        token = MockToken(api_key=auth_header)
        user_info = self.TOKEN_USER_DATABASE.get(token.api_key)
        user = MockUser(name=user_info[0])
        if not user.name:
            raise NotAuthorizedException()
        return AuthenticationResult(user=user, auth=token)


CustomAuthenticationMiddlewareUsageExample = """
使用示例如下：
```python
auth_mw = DefineMiddleware(CustomAuthenticationMiddleware, exclude="schema")

app = Litestar(
    route_handlers=[some_handler],
    middleware=[auth_mw]
)

# 在视图函数中使用
@get("/")
def my_http_handler(request: Request[MockUser, MockUser, State]) -> None:
    user = request.user  # correctly typed as MockUser
    auth = request.auth  # correctly typed as MockUser
    assert isinstance(user, MockUser)
    assert isinstance(auth, MockUser)
    
# 在依赖中使用
async def my_dependency(request: Request[MockUser, MockUser, State]) -> Any:
    user = request.user  # correctly typed as MockUser
    auth = request.auth  # correctly typed as MockUser
    assert isinstance(user, MockUser)
    assert isinstance(auth, MockUser)
```
所有请求都会先经过这个认证中间件。
"""


# ----------------------- JWT认证中间件使用 ---------------------
MOCK_DB: dict[str, User] = {
        "XiaoMing": User(uid="uid-1", name="XiaoMing", age=20, role="admin"),
        "XiaoHong": User(uid="uid-2", name="XiaoHong", age=18, role="normal")
}

async def retrieve_user_handler(token: Token, connection: ASGIConnection) -> User | None:
    """
    登录时，Token验证通过后，调用此方法获取用户信息
    :param token:
    :param connection:
    :return:
    """
    return MOCK_DB.get(token.sub)


async def guard_admin(connection: ASGIConnection, handler: BaseRouteHandler) -> None:
    """
    检查是否有 admin 角色权限的 Guard
    :param connection:
    :param handler:
    :return:
    """
    user: User = connection.user
    if user.role != "admin":
        raise NotAuthorizedException(detail=f"user {user.name} has no admin role")


jwt_auth = JWTAuth[User](
    token_secret="JWT_SECRET",
    # 要记得排除掉 OpenAPI 文档的视图路径和认证登录的路径
    exclude=[
        r"^/$",  # 根路径的排除要注意，不使用 ^ 和 $ 界定的话，会将所有路由都排除掉
        "/schema",
        "/router",
        "/controller",
        "/dependency",
        "/auth/login"
    ],
    # 配置用户检索回调函数
    retrieve_user_handler=retrieve_user_handler,
    # guards=[guard_admin]  # 也可以在 Router、Controller 中设置
)
