from typing import Annotated, Union
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestFormStrict
from jose import jwt, ExpiredSignatureError, JWTError  # 完成JWT验证的工具
from passlib.context import CryptContext  # 用于对密码进行hash处理和校验 —— 这里其实不太需要

from settings import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def generate_token(data: dict, expires_time: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_time:
        expire = datetime.utcnow() + expires_time
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"expiration": expire})
    # 生成 token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire.strftime("%Y-%m-%d")

# ----------------------------------------------------------------------------
# 下面就是处理 token 认证的依赖。
# 所有的依赖，最里层都必须要依赖于 OAuth2PasswordBearer 类的实例对象 oauth2_scheme，因为 oauth2_scheme 会负责从请求中解析 token 相关的信息。
# 但是 OAuth2PasswordBearer 也只负责解析出 token，其他的认证、角色控制等操作，都需要自己定义依赖来完成
# 下面的依赖，仿照的是 flask_httpauth 的 HTTPTokenAuth 功能来做的

async def verify_token(token: Annotated[str, Depends(oauth2_scheme)]):
    pass


async def get_user_roles():
    pass


async def login_required():
    pass


async def get_current_user(token):
    pass