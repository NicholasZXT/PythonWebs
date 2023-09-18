from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestFormStrict
from fastapi.responses import Response, JSONResponse, PlainTextResponse, HTMLResponse
from datetime import datetime, timedelta
from settings import AUTHORIZED_USERS, ACCESS_TOKEN_EXPIRE_SECONDES
from .schemas import Token, User
from dependencies.auth_dep import oauth2_scheme, generate_token, get_password_hash, verify_password, \
    verify_token, get_user_roles, login_required_as_admin, login_required_as_other

auth_router = APIRouter()

@auth_router.get("/hello")
async def hello_auth():
    html = "<h1>Hello FastAPI for OAuth Demo !</h1>"
    return HTMLResponse(content=html)

# 下面这个视图函数的 URL 必须要在 OAuth2PasswordBearer 实例化时的 tokenUrl 里指定
@auth_router.post("/get_token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestFormStrict, Depends()]):
    username = form_data.username
    passwd = form_data.password
    grant_type = form_data.grant_type
    # print(f"username: {username}")
    if grant_type is None or grant_type != 'password':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The grant type must be password")
    if username is None or passwd is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty user or password is forbidden")
    user_config = AUTHORIZED_USERS.get(username, {})
    # print(f"user_config: {user_config}")
    user_passwd = user_config.get('passwd', '')
    # 这里场景比较简单，其实可以不用做password的hash，不过正常情况下是要做hash的
    user_passwd_hash = get_password_hash(user_passwd)
    # if username not in AUTHORIZED_USERS or passwd != user_passwd:
    if username not in AUTHORIZED_USERS or not verify_password(passwd, user_passwd_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user or password")
    expire = timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDES)
    token, expiration = generate_token({'username': username}, expires_time=expire)
    return {'access_token': token, 'token_type': "Bearer", 'expires_in': str(ACCESS_TOKEN_EXPIRE_SECONDES)}


@auth_router.get("/show_token")
async def show_token(token: Annotated[str, Depends(oauth2_scheme)]):
    print("show_token: ", token)
    return {'token': token}


@auth_router.get("/test_token", dependencies=[Depends(verify_token)])
async def test_token():
    return HTMLResponse(content="<h1>Congratulations for passing token authorization!</h1>")


@auth_router.get("/show_user_roles")
async def show_user_roles(user: Annotated[User, Depends(verify_token)],
                          user_roles: Annotated[List[str], Depends(get_user_roles)]):
    return {'current_user': user.username, 'user_roles': user_roles}


@auth_router.get("/test_admin_role", dependencies=[Depends(login_required_as_admin)])
async def test_admin_roles(user: Annotated[User, Depends(verify_token)],
                          user_roles: Annotated[List[str], Depends(get_user_roles)]):
    return {'current_user': user.username, 'user_roles': user_roles, 'description': 'passed admin role authority'}


@auth_router.get("/test_other_role", dependencies=[Depends(login_required_as_other)])
async def test_other_roles(user: Annotated[User, Depends(verify_token)],
                          user_roles: Annotated[List[str], Depends(get_user_roles)]):
    return {'current_user': user.username, 'user_roles': user_roles, 'description': 'passed others role authority'}