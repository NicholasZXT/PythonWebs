from typing import Annotated, Union, List, Set
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
import jwt

from config import settings
from auth_app.schemas import AuthUser
from fastapi_login import LoginManager


# ------------------------- 自己实现的 JWT 登录验证过程相关依赖 -------------------------
# tokenUrl 的作用是指定 API 文档界面的 Authorize 按钮进行身份验证时要请求的URL，
# 这个设置错误的话，API 文档界面就无法使用 Authorize 功能，不过不影响接口的正常使用
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth_app/jwt/get_token")

# 下面是处理 token 认证的实现依赖。
# 所有的依赖，最里层都必须要依赖于 OAuth2PasswordBearer 类的实例对象 oauth2_scheme，因为 oauth2_scheme 会负责从请求中解析 token 相关的信息。
# 但是 OAuth2PasswordBearer 也只负责解析出 token，其他的认证、角色控制等操作，都需要自己定义依赖来完成

class PasswordUtil:
    """ 密码散列/校验的工具类，对 passlib 的 CryptContext 进行了简单封装 """
    def __init__(self, context: CryptContext):
        self.context = context

    def hash_password(self, password: str):
        return self.context.hash(password)

    def verify_password(self, plain_passwd: str, hashed_passwd: str):
        return self.context.verify(plain_passwd, hashed_passwd)


class TokenUtil:
    """ JWT的生成/校验工具类，基于 PyJWT"""
    def __init__(self, secret_key: str, algorithm: str, exp_default: int):
        self.secret = secret_key
        self.alg = algorithm
        self.exp_default = exp_default

    def generate_token(self, data: dict, expires_time: Union[timedelta, None] = None):
        payload = data.copy()
        if expires_time:
            expire = datetime.now(timezone.utc) + expires_time
        else:
            expire = datetime.now(timezone.utc) + timedelta(seconds=self.exp_default)
        expire_time_str = expire.strftime("%Y-%m-%d %H:%M:%S")
        payload.update({"exp": expire})
        payload.update({"expires_in": expire_time_str})
        # 生成 token
        encoded_jwt = jwt.encode(payload=payload, key=self.secret, algorithm=self.alg)
        return encoded_jwt, expire_time_str

    def verify_token(self, token: str):
        decoded_token = None
        try:
            decoded_token = jwt.decode(jwt=token, key=self.secret, algorithms=[self.alg])
        except jwt.ExpiredSignatureError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expires...")
        except jwt.PyJWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return decoded_token


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password_util = PasswordUtil(context=pwd_context)

token_util = TokenUtil(secret_key=settings.SECRET_KEY, algorithm=settings.ALGORITHM, exp_default=settings.ACCESS_TOKEN_EXPIRE_SECONDS)


async def authenticate_user(token: Annotated[str, Depends(oauth2_scheme)]):  # 这里使用了 OAuth2PasswordBearer 依赖来解析token
    """ 从请求中解析token，获取用户信息，并验证用户合法性 """
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
login_manager = LoginManager(
    secret=settings.SECRET_KEY,
    token_url="/auth_app/fastapi_login/login",
    algorithm='HS256',
    use_cookie=False,
    use_header=True,
    cookie_name="access_token",
    default_expiry=timedelta(seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS),
    # 这个 scopes 是父类 OAuth2PasswordBearer 提供的功能
    scopes={'admin': 'Admin role', 'others': 'Guest role'}
)

# 和 Flask-Login 类似，FastAPI-Login也需要使用装饰器来定义一个用户加载函数
@login_manager.user_loader
def load_user(user_name: str) -> AuthUser | None:
    user = settings.AUTHORIZED_USERS.get(user_name, None)
    if user:
        return AuthUser(username=user.get('username'), roles=user.get('roles'))
    else:
        return None



# ------------------------- AuthX 相关依赖 -------------------------



# ------------------------- fastapi-auth-jwt 相关依赖 -------------------------
