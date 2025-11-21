"""
研究整理 FastAPI 认证&鉴权 机制。
包含如下内容：
- 基于 OAuth2PasswordBearer，实现一个自定义 JWT 的认证过程
- 使用 FastAPI-Login 插件提供的认证实现
- 使用 AuthX 插件提供的认证实现
"""
from typing import Annotated, Union, List, Set
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
# HTTP 认证
from fastapi.security import HTTPBasic, HTTPBearer, HTTPDigest, HTTPBasicCredentials, HTTPAuthorizationCredentials
# OAuth2 认证
from fastapi.security import OAuth2PasswordBearer, OAuth2AuthorizationCodeBearer, SecurityScopes

# 两个比较好用的第三方认证插件
from fastapi_login import LoginManager
from authx import AuthX, AuthXConfig

from config import settings
from database import SessionLocalAsync
from auth_app.auth_utils import TokenUtil
from auth_app.schemas import AuthUser

# OAuth2PasswordBearer（或者其他fastapi.security里的认证类）在SwaggerUI上对应的是 Authorize 按钮里的验证，
# 但能在 SwaggerUI 里显示的前提是对应router里的某个视图函数里依赖了 OAuth2PasswordBearer 才能显示，否则不会出现在SwaggerUI里
# 说白了，就是要求：
# 1. 下面的 oauth2_scheme/login_manger 对象在 custom_jwt_router/login_router 里的某个视图函数里被依赖
# 2. custom_jwt_router/login_router 被 main.py 里的 FastAPI 对象 include
# 满足上面两个条件，FastAPI 对象才知道某个视图函数中使用了 security 里的对象，才会在 SwaggerUI 显示 Authorize 按钮
# 并且如果有多个 OAuth2PasswordBearer（及其子类）实例对象，Authorize 里也会显示多个登录验证框

# ------------------------- 自己实现的 JWT 登录验证过程相关依赖 -------------------------
# tokenUrl 的作用是指定 API 文档界面的 Authorize 按钮进行身份验证时要请求的URL，
# 这个设置错误的话，API 文档界面就无法使用 Authorize 功能，不过不影响接口的正常使用
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth_app/custom/login")

# 下面是处理 token 认证的实现依赖。
# 所有的依赖，最里层都必须要依赖于 OAuth2PasswordBearer 类的实例对象 oauth2_scheme，因为 oauth2_scheme 会负责从请求头中解析 token 相关的信息。
# 但是 OAuth2PasswordBearer 也只负责解析出 token，其他的认证、角色控制等操作，都需要自己定义依赖来完成

token_util = TokenUtil(secret_key=settings.SECRET_KEY, algorithm=settings.ALGORITHM, exp_default=settings.ACCESS_TOKEN_EXPIRE_SECONDS)


async def authenticate_user(token: Annotated[str, Depends(oauth2_scheme)]):
    """
    从请求中解析token，获取用户信息，并验证用户合法性。
    :param token: 使用了 OAuth2PasswordBearer 依赖来从请求头中解析 token 字符串
    :return:
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = token_util.verify_token(token)
    print(f"token_data: {token_data}")
    username: str = token_data.get("username", None)
    if username is None or username not in settings.AUTHORIZED_USERS:
        raise credentials_exception
    roles = settings.AUTHORIZED_USERS.get(username).get("roles", None)
    user = AuthUser(username=username, roles=roles)
    return user


async def get_user_roles(token_data: Annotated[AuthUser, Depends(authenticate_user)]):
    """
    身份验证通过后，基于用户身份获取用的角色。
    :param token_data: Depends(authenticate_user) 验证返回的用户身份
    :return:
    """
    username = token_data.username
    user_roles = settings.AUTHORIZED_USERS.get(username)['roles']
    return user_roles


# 下面的依赖，仿照的是 flask_httpauth 的 HTTPTokenAuth 功能来做的，实现类似于 HTTPTokenAuth 的 login_required 装饰器的作用
# 使用类作为依赖项，提供参数定义
class LoginRequired:
    def __init__(self, accept_roles: Set[str]):
        self.accept_roles = accept_roles

    # __call__ 方法里可以使用 异步的 依赖
    def __call__(self, user_roles: Annotated[List[str], Depends(get_user_roles)]):
        role_pass = False
        for role in user_roles:
            if role in self.accept_roles:
                role_pass = True
                break
        if not role_pass:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user roles are not allowed !")
        return role_pass


login_required_as_admin = LoginRequired(accept_roles={'admin'})
login_required_as_other = LoginRequired(accept_roles={'admin', 'others'})


# ------------------------- FastAPI-Login 相关依赖 -------------------------
# LoginManager 类继承自 OAuth2PasswordBearer
login_manager = LoginManager(
    secret=settings.SECRET_KEY,
    token_url="/auth_app/fastapi_login/login",
    algorithm='HS256',
    use_cookie=False,
    use_header=True,
    cookie_name="access_token",
    default_expiry=timedelta(seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS),
    # 这个 scopes 是父类 OAuth2PasswordBearer 提供的功能，这里传入的scopes会在 SwaggerUI 界面的 Authorize 里显示，
    # 告诉用户登录时，可以传入的scope，并不是起到限制作用
    scopes={'admin': 'Admin role', 'others': 'Guest role'}
)

# 和 Flask-Login 类似，FastAPI-Login也需要使用装饰器来注册一个用户加载函数
@login_manager.user_loader()
def load_user(user_name: str) -> AuthUser | None:
    """
    FastAPI-Login 的用户加载回调函数。
    :param user_name: 传入的参数就是创建token时传入的 sub 信息 —— 只能是 str 类型，int 类型在 jwt 解析token时会报错
    :return: 此函数的返回值就是后续 Depends(FastAPI-LoginManager) 处的返回值
    """
    # 模拟查询用户身份信息
    user = settings.AUTHORIZED_USERS.get(user_name, None)
    if user:
        return AuthUser(username=user_name, roles=user.get('roles'))
    else:
        return None

# 如果从数据库中查询用户信息，需要特别注意的是：由于 @login_manager.user_loader 不参与 FastAPI 的依赖注入过程，
# 因此不能使用 Depends(get_db_session_async) 的方式获得数据库 AsyncSession 对象
# 另外，由于 get_db_session_async 是一个 异步生成器，它用 yield 返回 AsyncSession，比较难处理
# 下面的这种方式，只能第一次请求时拿到 AsyncSession 对象，之后 yield 返回，for 循环也就结束了，这是个小坑 —————— KEY
# @login_manager.user_loader(db_gen=get_db_session_async())
# async def load_user(uid: str, db_gen: AsyncGenerator[AsyncSession, None]) -> User | None:
#     print(f">>>>> load_user_uid: {uid}")
#     async for db in db_gen:
#         async with db as session:
#             user = await session.get(User, uid)
#             print(f">>>>> load_user: {user}")
#             return user

@login_manager.user_loader()
async def load_user(uid: str) -> AuthUser | None:
    # print(f">>>>> load_user_uid: {uid}")
    # 只能自己直接实例化一个 AsyncSession 对象
    db_session = SessionLocalAsync()
    async with db_session as session:
        user = await session.get(AuthUser, uid)
        # print(f">>>>> load_user: {user}")
        return user


# ------------------------- AuthX 相关依赖 -------------------------
authx_config = AuthXConfig()
authx_config.JWT_ALGORITHM = "HS256"
authx_config.JWT_SECRET_KEY = settings.SECRET_KEY
# 默认 Token 获取位置
# authx_config.JWT_TOKEN_LOCATION = ["headers"]
authx_config.JWT_TOKEN_LOCATION = ["headers", "json"]
# 默认token过期时间
authx_config.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
authx = AuthX(config=authx_config)

# AuthX 的一个问题是，它没有继承 fastapi.security 里的 OAuth2PasswordBearer 等类，所以无法在 SwaggerUI 界面显示 Authorize 按钮
# 下面采用了一个取巧的办法，声明一个 OAuth2PasswordBearer，在 authx_router 里随便引入一下这个依赖
authx_scheme = OAuth2PasswordBearer(tokenUrl="auth_app/authx/login", scheme_name="AuthX")


# ------------------------- fastapi-auth-jwt 相关依赖 -------------------------
# from fastapi_auth_jwt import AuthConfig, JWTAuthBackend
# auth_config = AuthConfig(secret=settings.SECRET_KEY, expires_delta=timedelta(seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS))
# auth_backend = JWTAuthBackend(
#     authentication_config=auth_config,
#     # user_schema 只要是 pydantic.BaseModel 的子类即可
#     user_schema=AuthUser
# )
