# 所有扩展的依赖和对象的初始化都放到这里，以便进行模块拆分
import sys
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from flask import current_app, jsonify, request
from flask_httpauth import HTTPTokenAuth
from werkzeug.http import HTTP_STATUS_CODES
# itsdangerous 的 TimedJSONWebSignatureSerializer 只在 2.0.1 及其之前的版本中有，2.x 开始的官方文档建议转向 authlib
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired
from flask_login import LoginManager

# Web应用的用户认证
login_manager = LoginManager()

# Web-API的接口认证
auth = HTTPTokenAuth(scheme='Bearer')

LOG_FORMAT = "%(levelname)s, %(asctime)s, %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 日志配置
def getLogger(log_file: str, name: str = None):
    name = name if name else __name__
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    # 控制台输出
    console_handler = logging.StreamHandler()
    # console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(formatter)
    # 轮换文件输出
    # 每隔 interval 轮换一次， when 为单位，M 表示分钟 —— 每分钟轮换一次日志文件
    rotate_handler = TimedRotatingFileHandler(filename=log_file, when='M', interval=1, encoding='utf-8')
    # 每天轮换一次日志文件
    # rotate_handler = TimedRotatingFileHandler(filename=log_file, when='D', interval=1, encoding='utf-8')
    # 每周一轮换一次文件
    # rotate_handler = TimedRotatingFileHandler(filename=log_file, when='W0', encoding='utf-8')
    rotate_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.addHandler(rotate_handler)
    return logger


logger = getLogger('user_access_log', 'AuthLogging')

@auth.verify_token
def verify_token(token):
    """
    此函数接收请求中附带的token字符串，然后返回验证结果.
    可以返回下列两种结果之一：
    1. True 或者 False，简单的表示当前token的验证是否通过，不过这样有个缺点，此时 HTTPTokenAuth.current_user() 方法就拿不到用户名了
    2. 返回验证后的user object，最好是用户名的字符串，此时 HTTPTokenAuth.current_user() 就能拿到用户名了
    注意，如果验证不通过，应当返回 False 或者 None
    :param token:
    :return:
    """
    s = Serializer(secret_key=current_app.config['SECRET_KEY'])
    host = request.host
    access_url = request.url
    try:
        data = s.loads(token)
    except (BadSignature, SignatureExpired):
        logger.warning(f"BadRequest, {None}, {host}, {access_url}")
        return False
    user_name = data['user']
    user_config = current_app.config['AUTHORIZED_USERS'].get(user_name, None)
    if user_config is None:
        logger.warning(f"Unknown User, {user_name}, {host}, {access_url}")
        return None
    else:
        # 为了配合下面的 get_user_roles 使用，这里必须要返回用户名，而不能返回 True
        # return user_name
        # 更近一步，返回的信息里带有 user 的 roles 信息，这样时为了方便 HTTPTokenAuth.current_user() 里拿到 user 的 roles 信息
        user_roles = user_config['roles']
        logger.info(f"Authorized User, {user_name}, {host}, {access_url}")
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


# -------------------------------------------------------------------------------------
# 在 login_manager 中注册一个 user_loader 函数，用于配合 Flask-login 提供的 current_user 使用
# 如果用户已登录，current_user 会调用此处返回加载的 User 类对象；
# 如果用户未登录，则返回 Flask-login 内置的 AnonymousUserMixin 类对象
@login_manager.user_loader
def load_user(uid):
    from auth_app.models import User
    user = User.query.get(int(uid))
    print(f"@login_manager.user_loader get user [id={uid}, username={user.username}].")
    return user

# 设置访问需要登录资源时，自动跳转的登录视图的端点值（包括蓝本名称的完整形式）
# 如果不设置这个，访问需要登录的资源时，会返回 401 Unauthorized 的简单HTML页面
login_manager.login_view = "login_bp.to_login"