# auth_app所有扩展的依赖和对象的初始化都放到这里，以便进行模块拆分
import sys
import os
from flask import current_app, jsonify, request
from flask_login import LoginManager
from flask_httpauth import HTTPTokenAuth
from werkzeug.http import HTTP_STATUS_CODES
# itsdangerous 的 TimedJSONWebSignatureSerializer 只在 2.0.1 及其之前的版本中有，2.x 开始的官方文档建议转向 authlib
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired
from flask_jwt_extended import JWTManager
# from flask_principal import Principal, Identity
from .principal import Principal, Identity, identity_loaded, RoleNeed
from flask_security import Security
from extensions import getLogger
from auth_app.models import User, user_datastore

# 日志配置
logger = getLogger('auth_access.log', 'AuthLogging')

# Web-Session的用户认证
login_manager = LoginManager()

# Web-API的接口认证
http_auth = HTTPTokenAuth(scheme='Bearer')

# Web-API的JWT认证
jwt = JWTManager()

# Flask-Principal扩展
# principal = Principal()
principal = Principal(use_sessions=False)  # 禁止使用session，此时不会自动添加任何identity_loader函数，必须要手动设置至少一个

# Flask-Security扩展
"""
个人感觉Flask-Security做的有点臃肿了，为了大而全，集成了一些不那么必要的内容。
下面 Security 对象在实例化的时候，主要会干下面几件事：
1. 实例化一个 Flask-Login 对象 + Flask-Principal 对象，这两个算是必要的
2. 实例化一大堆Form相关的组件，这个感觉不是很有必要
3. 实例化一些工具类，比如密码工具类
4. 默认下（参数register_blueprint=True）会生成一个名称为 'security' 的 blueprint，里面定义了一些用于登录、登出、验证的视图函数，这些视图
   函数都和对应的 Form 类结合在一起使用，并且返回了一个渲染好的 简单的 html 页面。
   这个操作感觉也不是很必要，特别是现在前后端分离的趋势下，前端的Form基本不需要后端来渲染或者生成HTML代码了。
5. 将Flask-Security的所有可配置属性，都注册成当前 Flask对象（app）的属性 —— 这个操作感觉更没有必要
在实例化的时候，可以通过 register_blueprint=False 参数，禁止生成一个 'security' 的蓝图，这样一般就不会使用它附带定义的各种Form，然后
只使用 flask_security.decorators 提供的各种装饰器进行用户认证+权限校验，使用 Security.datastore 提供的各种方法来对用户、角色进行 CRUD
操作和检查，自定义的程度稍微高一点。
"""
# security = Security(datastore=user_datastore)
security = Security(datastore=user_datastore, register_blueprint=False)


# --------------------- Flask-Login 的hook函数 ---------------------------------
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


# -------------------- Flask-HttpAuth 的hook函数 --------------------------------
# Flask-HttpAuth 只是封装了各类认证方案（HTTPBasicAuth, HTTPTokenAuth等）的流程框架，但是流程中的具体细节，比如token生成，token验证
# 等逻辑的实现，需要我们手动在下面的hook函数中实现
@http_auth.verify_token
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

@http_auth.get_user_roles
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

@http_auth.error_handler
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

# -------------------- Flask-JWT-Extended 的hook函数 --------------------------------
# 相比于Flask-HttpAuth，Flask-JWT-Extended只提供基于token的认证，它不仅实现了认证的框架流程，还帮我们实现了上述token生成、token认证的过程
# 使用起来更方便，因此 Flask-JWT-Extended 需要实现的hook函数比较少

# 第1个要实现的hook函数是从用户对象中获取用户唯一标识的信息
# @jwt.user_identity_loader
def get_user_identity(userdata):
    """
    根据用户传入的数据，提取用户唯一标识信息，比如用户ID，这个信息后续被写入JWT的token中，
    存放在 JWT_IDENTITY_CLAIM参数（默认为sub）设置的 key 下。
    get_jwt_identity() 方法读取的就是这里的返回值。
    :param userdata: 传入的 userdata 可以是任何Python对象.
      实际上，这里传入的 userdata 就是 create_access_token() 或者 create_refresh_token() 方法里 identity 参数接收的python对象。
    :return: 返回能够标识用户唯一性的信息。
      实际上，也可以返回一些附加信息，唯一的硬性要求是能够被序列化。
    """
    # 这里假设传入的参数userdata是我们自己定义的User模型对象，返回的是用户ID+用户名
    return {'uid': userdata.uid, 'username': userdata.username}

# 第2个hook函数用于从 JWT头信息 和 JWT payload 里，获取用户相关的信息
# @jwt.user_lookup_loader
def user_lookup_callback(jwt_header, jwt_data):
    """
    这个回调函数必须接受两个参数，然后根据这两个参数附带的JWT信息，提取用户信息并返回（可以是任何Python对象）.
    返回值实际上会被以 {'loader_user': data} 的形式，存入 g._jwt_extended_jwt_user 这个属性里。
    返回值后续可以通过两种方式访问到：
      1. flask_jwt_extended.current_user 这个常量
      2. flask_jwt_extended.get_current_user() 方法的返回值
    :param jwt_header: 第1个参数是一个dict，存放了JWT的 header
    :param jwt_data: 第2个参数也是一个dict，存放了JWT的 payload
      上面 @jwt.user_identity_loader 设置的回调函数存入的信息就存放在payload里的 JWT_IDENTITY_CLAIM参数（默认为sub）设置的key里
    :return: 要么是包含用户信息的 任意Python对象，要么是 None
    """
    # 默认下，identity信息是存放在 jwt_data 字典里的 JWT_IDENTITY_CLAIM参数（默认为sub）设置的 key 下
    identity = jwt_data["sub"]
    # 可以通过identity提供的用户标识从数据库中查询用户信息
    # return User.query.filter_by(id=identity['uid']).one_or_none()
    # 这里直接返回也可以
    return identity

# ****** 下面是不需要访问数据库的版本，用于快速验证 *****
@jwt.user_identity_loader
def get_user_identity_mock(userdata):
    # 由于视图函数login_mock里，create_access_token()的identity是一个dict，包含了我们想要的信息，这里直接原样返回就可以了
    print(f"user_lookup_callback[mock] - userdata: {userdata}")
    return userdata

@jwt.user_lookup_loader
def user_lookup_callback_mock(jwt_header, jwt_data):
    identity = jwt_data["sub"]
    print(f"user_lookup_callback[mock] - identity: {identity}")
    # 这里也直接返回就可以了
    return identity

# ----------------------- Flask-Principal 的hook函数 ----------------------------
# @principal.identity_loader
# def load_user_identity():
#     pass

@identity_loaded.connect
def principal_identity_loaded(sender, identity: Identity):
    """
    在这个回调函数里根据用户ID，添加用户的权限
    """
    # print(f"principal_identity_loaded: prepare to add roles for {identity}")
    current_app.logger.debug(f"principal_identity_loaded: prepare to add roles for {identity}")
    authorized_users = current_app.config['AUTHORIZED_USERS']
    user_config = authorized_users.get(identity.id, {})
    if user_config:
        for role in user_config['roles']:
            role_need = RoleNeed(role)
            # print(f"principal_identity_loaded: add RoleNeed '{role_need}' for identity: {identity}")
            current_app.logger.debug(f"principal_identity_loaded: add RoleNeed '{role_need}' for identity: {identity}")
            identity.provides.add(role_need)

