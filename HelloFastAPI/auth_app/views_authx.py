"""
练习 AuthX 使用
"""
from fastapi import APIRouter, Depends, HTTPException, status, Security, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.security import OAuth2PasswordRequestForm, SecurityScopes
from typing import Annotated, List

from config import settings
from .auth_dependencies import authx, authx_scheme
from .schemas import AuthUser, RefreshBody
from authx import TokenPayload, RequestToken

authx_router = APIRouter(
    prefix='/auth_app/authx',
    tags=['Auth-App-AuthX']
)

@authx_router.post('/login')
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user or password")
    # 用户名和密码校验通过，生成JWT
    # 附加的信息可以通过 data 参数传入，比如这里的 roles —— 这一点和官方文档说明不一样，官方文档说是关键字参数传入，但查看源码可以发现是用data参数
    token = authx.create_access_token(uid=username, data={"roles": user_config.get('roles', [])})
    # 支持设置刷新token
    refresh_token = authx.create_refresh_token(uid=username, data={"roles": user_config.get('roles', [])})
    return {'token_type': 'Bearer', 'access_token': token, 'refresh_token': refresh_token}


# 刷新token视图函数
@authx_router.post('/refresh')
async def refresh(request: Request, body: RefreshBody):
    # 这里的RefreshBody只是为了能够在 SwaggerUI 中传递POST请求体，并且它的token字段名称必须要和 AuthXConfig.JWT_REFRESH_JSON_KEY 一致
    """ Refresh Token 视图函数 """
    try:
        # 这里需要注意 JWT_TOKEN_LOCATION 配置项里有 headers, json
        refresh_payload = await authx.refresh_token_required(request)
        access_token = authx.create_access_token(refresh_payload.sub, data={"roles": refresh_payload.roles})
        return {"access_token": access_token}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


# 下面这个视图函数是为了引入 authx_scheme， 从而能在 SwaggerUI 显示 Authorize Button，不过下面的视图函数也依赖了，此处就不必了
@authx_router.get('/scheme', dependencies=[Depends(authx_scheme)])
def scheme():
    return {"message": "For SwaggerUI Authorize Button"}


# dependencies 中使用 Depends(authx_scheme) 是为了配合 SwaggerUI 界面的 Authorize Button 使用，只有依赖了这个
# 在 SwaggerUI 界面调试时请求体才会带入 Authorize Button 登录时的 token 信息
@authx_router.get(
    path="/protected",
    dependencies=[Depends(authx_scheme), Depends(authx.access_token_required)]
)
def get_protected():
    """ 访问受保护视图函数 """
    return {"message": "Hello World for AuthX Protected View"}


@authx_router.get("/protected/v2", dependencies=[Depends(authx_scheme)])
def get_payload(payload: TokenPayload = Depends(authx.access_token_required)):
    """ 展示获取Token里payload里的附加信息 """
    return {
        "id": payload.sub,
        # 获取 payload 里的自定义附加信息
        "roles": getattr(payload, "roles")
    }
