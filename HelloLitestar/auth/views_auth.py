from typing import TYPE_CHECKING
from datetime import timedelta
from litestar import Controller, Request, Response, get, post, put, delete
from litestar.exceptions import HTTPException, NotAuthorizedException
from .models import User
from .middlewares_auth import guard_admin, jwt_auth, MOCK_DB


class AuthController(Controller):
    path = '/auth'
    tags = ['Auth']
    # middleware = []
    # guards = [guard_admin]

    @get(path='/')
    async def hello(self, request: Request) -> str:
        return "Hello to AuthController!"

    @post(path='/login')
    async def login(self, request: Request, user_name: str) -> str:
        request.logger.info(f">>> login called from user: {user_name}...")
        if user_name not in MOCK_DB:
            raise NotAuthorizedException(f"User '{user_name}' not found")
        user: User = MOCK_DB[user_name]
        return jwt_auth.login(identifier=user_name, token_expiration=timedelta(minutes=60), token_extras={"role": user.role})

    @get(path='/sec')
    async def sec_view(self, request: Request) -> str:
        user: User = request.user
        return f"sec_view is accessed by user: {user.name}."

    @get(path='/admin', guards=[guard_admin])
    async def admin_view(self, request: Request) -> str:
        user: User = request.user
        return f"admin_view is accessed by user: {user.name}."

    # 此视图函数排除认证
    @get(path='/skip', exclude_from_auth=True)
    async def skip_view(self, request: Request) -> str:
        request.logger.info(f"[skip_view] request.user exist: {hasattr(request, 'user')}")
        # request.logger.info(f"[skip_view] request.user exist...")
        return "skip_view is accessed."


