# 所有扩展的依赖和对象的初始化都放到这里，以便进行模块拆分
import sys
import os
from flask import current_app, jsonify, request
from flask_login import LoginManager
from flask_httpauth import HTTPTokenAuth
from werkzeug.http import HTTP_STATUS_CODES
# itsdangerous 的 TimedJSONWebSignatureSerializer 只在 2.0.1 及其之前的版本中有，2.x 开始的官方文档建议转向 authlib
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired
from HelloFlask.extensions import getLogger
from auth_app.models import User

# 日志配置
logger = getLogger('user_access_log', 'AuthLogging')

# Web-session的用户认证
login_manager = LoginManager()

# Web-API的接口认证
auth = HTTPTokenAuth(scheme='Bearer')

# --------------------- Flask-Login 的回调函数 ---------------------------------
# 必须要在 login_manager 中注册一个 user_loader 函数，用于配合 Flask-Login 提供的 current_user 使用
# 如果用户已登录，current_user 会调用此处返回加载的 User 类对象；
# 如果用户未登录，则返回 Flask-Login 内置的 AnonymousUserMixin 类对象
@login_manager.user_loader
def load_user(uid):
    user = User.query.get(int(uid))
    print(f"@login_manager.user_loader get user [id={uid}, username={user.username}].")
    return user


# 设置访问需要登录资源时，自动跳转的登录视图的端点值（包括蓝本名称的完整形式）
# 如果不设置这个，访问需要登录的资源时，会返回 401 Unauthorized 的简单HTML页面
login_manager.login_view = "login_bp.to_login"

# -------------------- Flask-HttpAuth 的回调函数 --------------------------------
@auth.verify_token
def verify_token(token):
    """
    此函数接收请求中附带的token字符串，然后返回验证结果.
    可以返回下列两种结果之一：
    1. True 或者 False，简单的表示当前token的验证是否通过，不过这样有个缺点，此时 HTTPTokenAuth.current_user() 方法就拿不到用户名了
    2. 返回验证后的user object，最好是用户名的字符串，此时 HTTPTokenAuth.current_user() 就能拿到用户名了
    注意，如果验证不通过，应当返回 False 或者 None。
    使用Nginx做反向代理时，还需要配置如下项目，才能拿到源主机的IP地址：
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header REMOTE-HOST $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    :param token:
    :return:
    """
    s = Serializer(secret_key=current_app.config['SECRET_KEY'])
    # 尝试获取访问的源主机/IP地址
    host = request.host
    access_url = request.url
    remote_addr = request.remote_addr
    # 使用Nginx做反向代理时，只有这个能拿到代理前的源主机IP地址
    forwarded = request.headers.get('x-forwarded-for', None)
    # 解析token的内容
    try:
        data = s.loads(token)
    except (BadSignature, SignatureExpired):  # 解析失败，或者签名过期
        logger.warning(f"BadRequest, {None}, {host}, {remote_addr}, {forwarded}, {access_url}")
        return False
    # 解析Token成功，从解析后的data中获取用户名
    user_name = data['user']
    # 根据用户名查询用户的配置，正常是要访问数据库的，这里简化了，直接从配置文件中读取提前设定的用户
    user_config = current_app.config['AUTHORIZED_USERS'].get(user_name, None)
    if user_config is None:
        # 加了一个记录用户访问记录的功能
        logger.warning(f"Unknown User, {user_name}, {host}, {remote_addr}, {forwarded}, {access_url}")
        return None
    else:
        # 为了配合下面的 get_user_roles 使用，这里必须要返回用户名，而不能返回 True
        # return user_name
        # 更近一步，返回的信息里带有 user 的 roles 信息，这样时为了方便 HTTPTokenAuth.current_user() 里拿到 user 的 roles 信息
        user_roles = user_config['roles']
        # 加了一个记录用户访问记录的功能
        logger.info(f"Authorized User, {user_name}, {host}, {remote_addr}, {forwarded}, {access_url}")
        return {'user': user_name, 'roles': user_roles}

@auth.get_user_roles
def get_user_roles(user):
    """
    获取用户的角色.
    :param user: user 就是上面 HTTPTokenAuth.verify_token 回调函数的返回值
    :return:
    """
    # 如果上面只返回了user的name时
    # user_config = current_app.config['AUTHORIZED_USERS'].get(user, None)
    # 如果上面返回的是 user 的dict
    user_name = user['user']
    user_config = current_app.config['AUTHORIZED_USERS'].get(user_name, None)
    if user_config is None:
        return 'nobody'  # 任意用户
    else:
        return user_config['roles']

@auth.error_handler
def auth_error(status):
    return "Access Denied", status

def generate_token(user):
    """使用 itsdangerous库 生成序列化的Token"""
    expiration = current_app.config['TOKEN_EXPIRATION']
    s = Serializer(secret_key=current_app.config['SECRET_KEY'], expires_in=expiration)
    token = s.dumps({'user': user}).decode()
    return token, expiration

def api_abort(code, message=None, **kwargs):
    if message is None:
        message = HTTP_STATUS_CODES.get(code, '')
    response = jsonify(code=code, message=message, **kwargs)
    response.status_code = code
    return response
