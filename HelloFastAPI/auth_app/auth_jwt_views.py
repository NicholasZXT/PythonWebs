from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, JSONResponse, PlainTextResponse, HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated, List
from config import settings
from .schemas import Token, AuthUser
from .dependencies import oauth2_scheme, password_util, token_util, authenticate_user, get_user_roles, \
    login_required_as_admin, login_required_as_other

"""
展示FastAPI下，使用 Bearer JWT 令牌的验证方式
"""
auth_jwt_router = APIRouter(
    prefix='/auth_app',
    tags=['Auth-JWT-App']
)


@auth_jwt_router.get("/", tags=['Hello'])
async def hello_auth_jwt():
    html = "<h1>Hello FastAPI for Auth with JWT Demo !</h1>"
    return HTMLResponse(content=html)

# 下面这个视图函数的 URL 需要在 OAuth2PasswordBearer 实例化时的 tokenUrl 里指定，才能在 API 文档界面使用 Authorize 按钮的功能
@auth_jwt_router.post("/get_token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    # OAuth2PasswordRequestForm 表示从表单获取用户名和密码，并且key必须为 username 和 password
    """ 登录并获取用户的JWT """
    username = form_data.username
    passwd = form_data.password
    grant_type = form_data.grant_type
    # print(f"username: {username}")
    if grant_type is None or grant_type != 'password':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The grant type must be password")
    if username is None or passwd is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty user or password is forbidden")
    user_config = settings.AUTHORIZED_USERS.get(username, {})
    # print(f"user_config: {user_config}")
    passwd_to_check = user_config.get('passwd', '')
    # ----------------------------------------------------------------------------------------------------
    # 真实场景下，上面拿到的 passwd_to_check 应该是经过哈希散列后的值，然后和用户登录时发送的密码 passwd 进行比对
    # user_passwd_hash = password_util.hash_password(passwd_to_check)
    # if username not in AUTHORIZED_USERS or not password_util.verify_password(passwd, user_passwd_hash):
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user or password")
    # ----------------------------------------------------------------------------------------------------
    # 这里简化起见，不做password的hash，直接比对密码
    if username not in settings.AUTHORIZED_USERS or passwd != passwd_to_check:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user or password")
    # 用户名和密码校验通过，生成JWT
    token, expiration = token_util.generate_token(data={'username': username})
    return {'access_token': token, 'token_type': "Bearer", 'expires_in': expiration}


@auth_jwt_router.get("/show_token", response_class=JSONResponse)
async def show_token(token: Annotated[str, Depends(oauth2_scheme)]):
    """ 显示当前用户的Token内容 """
    print("show_token -> token: ", token)
    decoded_token = token_util.verify_token(token)
    return {'token': token, 'decoded_token': decoded_token}


@auth_jwt_router.get("/test_token", response_class=HTMLResponse)
async def test_token(user: AuthUser = Depends(authenticate_user)):
    """ 验证是否通过Token校验 """
    html = f"<h1>Congratulations for passing token authorization with user '{user.username}' !</h1>"
    return HTMLResponse(content=html)


@auth_jwt_router.get("/show_user_roles", response_class=JSONResponse)
async def show_user_roles(
    user: Annotated[AuthUser, Depends(authenticate_user)],
    user_roles: Annotated[List[str], Depends(get_user_roles)]
):
    """ 显示当前用户所属的roles """
    return {'current_user': user.username, 'user_roles': user_roles}

# 使用了自定义的依赖来校验用户角色，这里依赖是放在路由函数中的
@auth_jwt_router.get("/test_admin_role", response_class=JSONResponse, dependencies=[Depends(login_required_as_admin)])
async def test_admin_roles(
    user: Annotated[AuthUser, Depends(authenticate_user)],
    user_roles: Annotated[List[str], Depends(get_user_roles)]
):
    """ 验证admin角色组 """
    return {'current_user': user.username, 'user_roles': user_roles, 'description': 'passed admin role authority'}

# 这里将角色校验依赖放在了视图函数参数里，原因是 login_required_as_other 中其实也调用了 get_user_roles -> authenticate_user，
# 放在一起似乎能使用依赖解析的缓存？
@auth_jwt_router.get("/test_other_role", response_class=JSONResponse)
async def test_other_roles(
    user: Annotated[AuthUser, Depends(authenticate_user)],
    user_roles: Annotated[List[str], Depends(get_user_roles)],
    role_pass: Annotated[bool, Depends(login_required_as_other)]
):
    """ 验证others角色组 """
    print("role_pass: ", role_pass)
    return {'current_user': user.username, 'user_roles': user_roles, 'description': 'passed others role authority'}
