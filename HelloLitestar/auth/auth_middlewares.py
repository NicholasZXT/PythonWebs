"""
Litestar 提供的鉴权机制也是采用中间件形式来实现的。
"""
from litestar.enums import ScopeType
from litestar.middleware import AbstractAuthenticationMiddleware, AuthenticationResult
from litestar.datastructures import MutableScopeHeaders
from litestar.types import ASGIApp, Message, Receive, Scope, Send
from litestar.connection import ASGIConnection
from litestar.security import AbstractSecurityConfig
