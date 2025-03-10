from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated, List
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
    # 用户名和密码校验通过，生成JWT
    token = login_manager.create_access_token(data={'sub': username}, scopes=user_config.get('roles', None))
    return {'access_token': token, 'token_type': "Bearer"}


@login_router.get("/protected")
def protected_route(user=Depends(login_manager)):
    return {"user": user}


@login_router.get("/test_admin", response_class=JSONResponse)
def test_admin(user: AuthUser = Security(login_manager, scopes=['admin'])):
    return {"user": user, "roles": user.roles}


@login_router.get("/test_others", response_class=JSONResponse)
def test_admin(user: AuthUser = Security(login_manager, scopes=['admin', 'others'])):
    return {"user": user, "roles": user.roles}
