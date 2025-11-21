"""
认证过程中，自定义实现的一些工具类
"""
from typing import Annotated, Union, List, Set
from datetime import datetime, timedelta, timezone
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status


class PasswordUtil:
    """
    密码散列/校验的工具类，对 passlib 的 CryptContext 进行了简单封装
    """
    def __init__(self, context: CryptContext):
        self.context = context

    def hash_password(self, password: str):
        return self.context.hash(password)

    def verify_password(self, plain_passwd: str, hashed_passwd: str):
        return self.context.verify(plain_passwd, hashed_passwd)


class TokenUtil:
    """
    JWT的生成/校验工具类，基于 PyJWT实现
    """
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
