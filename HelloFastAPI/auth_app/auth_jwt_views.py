from fastapi import APIRouter, Depends, HTTPException, status, Security, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.security import OAuth2PasswordRequestForm, SecurityScopes
from typing import Annotated, List

from config import settings
from .dependencies import auth_backend
from .schemas import AuthUser
from fastapi_auth_jwt import JWTAuthenticationMiddleware

# FastAPI-Auth-JWT 需要将 JWTAuthenticationMiddleware 添加到 FastAPI 的中间件列表中，这一点不太方便
# from fastapi import FastAPI
# app = FastAPI()
# app.add_middleware(
#     JWTAuthenticationMiddleware,
#     backend=auth_backend,
#     exclude_urls=["/sign-up", "/login"],  # Public endpoints
# )

"""
练习 FastAPI-Auth-JWT 使用
"""
auth_jwt_router = APIRouter(
    prefix='/auth_app/auth_jwt',
    tags=['Auth-App-FastAPI-Auth-JWT']
)

@auth_jwt_router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    username = form_data.username
    passwd = form_data.password
    grant_type = form_data.grant_type
    if grant_type is None or grant_type != 'password':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The grant type must be password")
    if username is None or passwd is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty user or password is forbidden")
    user_config = settings.AUTHORIZED_USERS.get(username, {})
    passwd_to_check = user_config.get('passwd', '')
    if username not in settings.AUTHORIZED_USERS or passwd != passwd_to_check:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user or password")
    # 用户名和密码校验通过，生成JWT
    token = await auth_backend.create_token(
        user_data={"username": username, "roles": user_config.get('roles', [])},
        expiration=settings.ACCESS_TOKEN_EXPIRE_SECONDS
    )
    return {'access_token': token, 'token_type': "Bearer"}

@auth_jwt_router.post("/sign-up")
async def sign_up(user: AuthUser):
    # Implement user creation logic here
    return {"message": "User created"}


@auth_jwt_router.get("/profile-info")
async def get_profile_info(request: Request):
    # 从 request.state.user 中获取用户信息
    user: AuthUser = request.state.user
    return {"username": user.username}

@auth_jwt_router.post("/logout")
async def logout(request):
    user = request.state.user
    await auth_backend.invalidate_token(user.token)
    return {"message": "Logged out"}
