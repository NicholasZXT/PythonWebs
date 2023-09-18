from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestFormStrict
from fastapi.responses import Response, JSONResponse, PlainTextResponse, HTMLResponse
from datetime import datetime, timedelta
from settings import AUTHORIZED_USERS, ACCESS_TOKEN_EXPIRE_SECONDES
from dependencies.auth_dep import oauth2_scheme, generate_token, get_password_hash, verify_password
from .schemas import TokenData

auth_router = APIRouter()

@auth_router.get("/hello/auth")
async def hello_auth():
    html = "<h1>Hello FastAPI for OAuth Demo !</h1>"
    return HTMLResponse(content=html)

@auth_router.post("/auth/get_token", response_model=TokenData)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestFormStrict, Depends()]):
    username = form_data.username
    passwd = form_data.password
    grant_type = form_data.grant_type
    if grant_type is None or grant_type != 'password':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The grant type must be password")
    if username is None or passwd is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty user or password is forbidden")
    user_config = AUTHORIZED_USERS.get(username, {})
    user_passwd = user_config.get('passwd', '')
    # 这里场景比较简单，其实可以不用做password的hash，不过正常情况下是要做hash的
    user_passwd_hash = get_password_hash(user_passwd)
    # if username not in AUTHORIZED_USERS or passwd != user_passwd:
    if username not in AUTHORIZED_USERS or verify_password(passwd, user_passwd_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user or password")
    expire = timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDES)
    token, expiration = generate_token({'user': username}, expires_time=expire)
    return {'access_token': token, 'token_type': "Bearer", 'expires_in': ACCESS_TOKEN_EXPIRE_SECONDES}


@auth_router.get("/auth/show_token")
async def show_token(token: Annotated[str, Depends(oauth2_scheme)]):
    print("token: ", token)
    return {'token': token}


@auth_router.get("")
async def test_token():
    return HTMLResponse(content="<h1>Congratulations for passing token authorization!</h1>")