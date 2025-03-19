from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Security, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.security import OAuth2PasswordRequestForm, SecurityScopes
from fastapi_login.exceptions import InvalidCredentialsException

from config import settings
from .dependencies import login_manager
from .schemas import AuthUser

"""
练习 FastAPI-Login 使用
"""
login_router = APIRouter(
    prefix='/auth_app/fastapi_login',
    tags=['Auth-App-FastAPI-Login']
)

@login_router.post("/login", response_class=JSONResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """ 登录并获取用户的JWT """
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
        # raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user or password")
        raise InvalidCredentialsException
    # 用户名和密码校验通过，生成JWT，这里 sub 的传入值就是 @login_manager.user_loader() 注册函数的接受的参数
    token = login_manager.create_access_token(data={'sub': username}, scopes=user_config.get('roles', None))
    return {'access_token': token, 'token_type': "Bearer"}


@login_router.get("/protected")
async def protected_route(user: AuthUser = Depends(login_manager)):
    """ 测试视图函数登录时需要验证用户 """
    # Depends(login_manager)的返回值就是 @login_manager.user_loader() 注册函数的返回值
    return {"user": user.username}


@login_router.get("/protected/v2", dependencies=[Depends(login_manager)])
async def protected_route_v2(request: Request):
    """ 测试视图函数登录时需要验证用户-v2 """
    # 在视图函数中获取当前用户的另一种方法
    token = await login_manager._get_token(request)
    user = await login_manager.get_current_user(token)
    return {"user": user.username}


@login_router.get("/test_admin", response_class=JSONResponse)
def test_admin(user: AuthUser = Security(login_manager, scopes=['admin'])):
    """ 验证用户同时，还要验证 scopes"""
    # 使用 FastAPI 提供的 Security 函数来接受需要校验的 scopes 列表，Security 类似于 Depends
    # 实际的 scopes 校验流程是在 LoginManager 的 __call__ 方法里执行的，该方法有一个参数 SecurityScopes，
    # 它是 FastAPI 提供的类似于 Request 的类，专门用于获取 Security 中的 scopes 列表？ —— 这一点有待深入研究
    # scopes 是一个列表，要求其中所有的scope都含有时才能通过验证
    return {"user": user.username, "roles": user.roles}


@login_router.get("/test_others", response_class=JSONResponse)
def test_other(user: AuthUser = Security(login_manager, scopes=['others'])):
    return {"user": user.username, "roles": user.roles}
