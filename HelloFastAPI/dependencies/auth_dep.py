from typing import Annotated, Union, List, Set
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestFormStrict
from jose import jwt, ExpiredSignatureError, JWTError  # 完成JWT验证的工具
from passlib.context import CryptContext  # 用于对密码进行hash处理和校验 —— 这里其实不太需要

from settings import SECRET_KEY, ALGORITHM, AUTHORIZED_USERS
from app_auth.schemas import User

# tokenUrl 必须指定验证获取token的视图函数
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth_app/get_token")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def generate_token(data: dict, expires_time: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_time:
        expire = datetime.now() + expires_time
    else:
        expire = datetime.now() + timedelta(minutes=15)
    to_encode.update({"expires_in": expire.strftime("%Y-%m-%d %H:%M:%S")})
    # 生成 token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire.strftime("%Y-%m-%d %H:%M:%S")

# ----------------------------------------------------------------------------
# 下面是处理 token 认证的依赖。
# 所有的依赖，最里层都必须要依赖于 OAuth2PasswordBearer 类的实例对象 oauth2_scheme，因为 oauth2_scheme 会负责从请求中解析 token 相关的信息。
# 但是 OAuth2PasswordBearer 也只负责解析出 token，其他的认证、角色控制等操作，都需要自己定义依赖来完成
# 下面的依赖，仿照的是 flask_httpauth 的 HTTPTokenAuth 功能来做的

async def verify_token(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 使用 JWT对 token 进行解析
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="token expires..")
    except JWTError:
        raise credentials_exception
    print(f"payload: {payload}")
    username: str = payload.get("username")
    if username is None or username not in AUTHORIZED_USERS:
        raise credentials_exception
    user = User(username=username)
    return user

async def get_user_roles(token_data: Annotated[User, Depends(verify_token)]):
    username = token_data.username
    user_roles = AUTHORIZED_USERS.get(username)['roles']
    return user_roles

# 下面这个是实现类似于 HTTPTokenAuth 的 login_required 装饰器的作用
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
