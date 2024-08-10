# auth_app所有扩展的依赖和对象的初始化都放到这里，以便进行模块拆分
import sys
import os
from functools import wraps
from flask import current_app, jsonify, request
from flask_login import LoginManager
from flask_httpauth import HTTPTokenAuth
from werkzeug.http import HTTP_STATUS_CODES
# itsdangerous 的 TimedJSONWebSignatureSerializer 只在 2.0.1 及其之前的版本中有，2.x 开始的官方文档建议转向 authlib
# from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import URLSafeTimedSerializer as Serializer
from itsdangerous import BadSignature, SignatureExpired
from flask_jwt_extended import JWTManager, get_current_user
# from flask_principal import Principal, identity_loaded, identity_changed, Identity, AnonymousIdentity, RoleNeed
from auth_app.principal import Principal, identity_loaded, identity_changed, Identity, AnonymousIdentity, RoleNeed
from extensions import getLogger
from auth_app.models import User
# Flask-Security扩展内部会实例化Flask-Login, Flask-Principal等扩展，和手动创建的实例可能有冲突，因此单独研究

# 日志配置
logger = getLogger('auth_access.log', 'AuthLogging')

# Web-Session的用户认证
login_manager = LoginManager()

# Web-API的接口认证
http_auth = HTTPTokenAuth(scheme='Bearer')

# Web-API的JWT认证
# JWTManager实例化的时候并不会做太多的操作，主要做两件事：
# 1. 向 app.config 里设置一些JWT用到的配置常量
# 2. 注册一些 error_handler_callback
jwt = JWTManager()

# Flask-Principal扩展
# 默认下，会提供一个使用 Flask 全局对象 session 存取用户身份的 identity_loader/identity_saver 函数，实现一个简单的跨请求的用户身份功能
# principal = Principal()
# 禁止使用session，此时不会自动添加任何 identity_loader/identity_saver 函数，必须手动设置一个
# 对于 REST-API 开发来说，一般不会跨请求保持状态（这里是用户身份信息），此时可以选择禁止使用 session
principal = Principal(use_sessions=False)

# ====================================== 各个扩展的hook函数 ======================================
def api_abort(code, message=None, **kwargs):
    """视图函数的统一错误响应返回函数"""
    if message is None:
        message = HTTP_STATUS_CODES.get(code, '')
    response = jsonify(code=code, message=message, **kwargs)
    response.status_code = code
    return response

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
def generate_token(user):
    """使用 itsdangerous库 生成序列化的Token"""
    expiration = current_app.config['TOKEN_EXPIRATION']
    # 使用旧版的 TimedJSONWebSignatureSerializer 实现
    # s = Serializer(secret_key=current_app.config['SECRET_KEY'], expires_in=expiration)
    # token = s.dumps({'user': user}).decode()
    # 使用 URLSafeTimedSerializer 实现，过期时间的检查放在了解析时设置
    s = Serializer(secret_key=current_app.config['SECRET_KEY'])
    token = s.dumps({'user': user})
    return token, expiration

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
    expiration = current_app.config['TOKEN_EXPIRATION']
    s = Serializer(secret_key=current_app.config['SECRET_KEY'])
    # 尝试获取访问的源主机/IP地址
    host = request.host
    access_url = request.url
    remote_addr = request.remote_addr
    # 使用Nginx做反向代理时，只有这个能拿到代理前的源主机IP地址
    forwarded = request.headers.get('x-forwarded-for', None)
    # 解析token的内容
    # 使用旧版的 TimedJSONWebSignatureSerializer 实现
    # try:
    #     data = s.loads(token)
    # except (BadSignature, SignatureExpired):  # 解析失败，或者签名过期
    #     logger.warning(f"BadRequest, {None}, {host}, {remote_addr}, {forwarded}, {access_url}")
    #     return False
    # 使用 URLSafeTimedSerializer 实现，过期时间的检查放在了解析时
    try:
        data = s.loads(token, max_age=expiration)
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

# -------------------- Flask-JWT-Extended 的hook函数 --------------------------------
# 相比于Flask-HttpAuth，Flask-JWT-Extended只提供基于token的认证，它不仅实现了认证的框架流程，
# 还实现了上述token生成、token认证的过程，使用起来更方便，因此 Flask-JWT-Extended 需要实现的hook函数比较少
# JWT需要关注的几个装饰器方法如下：
"""
@jwt.user_identity_loader 注册一个回调函数，用于 **创建JWT时** 从用户信息中提取用户唯一标识
 + 被装饰函数必须接受1个参数，该参数就是使用 create_access_token()/create_fresh_token() 时设置的 identity= 的参数值
 + 每次调用 create_access_token()/create_fresh_token() 时都会调用此回调函数
 + 返回值必须是可序列化的值，默认实现下，直接使用传入的 identity 参数值
 + 被装饰函数里，一般实现从 identity 对象中提取用户唯一标识符的逻辑
@jwt.user_lookup_loader 注册一个回调函数，用于 **从请求中解析JWT时** 将其中的信息转换成用户数据
 + 被装饰函数必须接受2个参数，第1个是JWT的header，第2个是JWT的payload，两者均为 dict
 + 返回值可以是任何Python对象，可以通过 current_user 或者 get_current_user() 访问
 + 通常在这里实现的逻辑是借助SQLAlchemy从数据库中查询token(JWT payload)中指定的用户
@jwt.user_lookup_error_loader 注册一个错误处理的回调函数，在 @jwt.user_lookup_loader 失败时调用
 + 参数和 @jwt.user_lookup_loader 的一样
 + 返回值必须是一个 Flask Response
@jwt.unauthorized_loader 注册回调函数，用于处理请求中不含JWT的情况
 + 被装饰函数必须接受1个参数，该参数是一个字符串，解释了为什么JWT无效
 + 返回值必须是一个 Flask Response
@jwt.additional_claims_loader 注册一个回调函数，用于在创建JWT时附加额外的信息
 + 被装饰函数必须接受1个参数，该参数就是使用 create_access_token()/create_fresh_token() 时 identity= 的参数值
 + 返回值是一个dict，该附加信息会被添加到JWT里
 + 也可以使用 create_access_token()/create_fresh_token() 的 additional_claims= 参数设置附加信息
@jwt.token_verification_loader 注册自定义JWT验证的函数
 + 被装饰函数必须接受2个参数，第1个是JWT的header，第2个是JWT的payload，两者均为 dict
 + 返回值必须为True/False
@jwt.token_verification_failed_loader 注册自定义JWT验证失败的回调函数
 + 被装饰函数必须接受2个参数，第1个是JWT的header，第2个是JWT的payload，两者均为 dict
 + 返回值必须为 Flask Response
当然，上述各个装饰器方法都设置了默认实现，在 default_callbacks.py 文件里
"""
# 第1个要实现的hook函数是从用户对象中获取用户唯一标识的信息
# @jwt.user_identity_loader
def get_user_identity(userdata):
    """
    创建JWT时使用.
    根据用户传入的数据，提取用户唯一标识信息，比如用户ID，这个信息后续被写入JWT的token中，
    存放在 JWT_IDENTITY_CLAIM参数（默认为sub）设置的 key 下。
    get_jwt_identity() 方法读取的就是这里的返回值。
    :param userdata: 传入的 userdata 可以是任何Python对象.
      实际上，这里传入的 userdata 就是 create_access_token()/create_refresh_token() 方法里 identity 参数的python对象。
    :return: 返回能够标识用户唯一性的信息。
      实际上，也可以返回一些附加信息，唯一的硬性要求是能够被序列化。
    """
    # 这里假设传入的参数userdata是我们自己定义的User模型对象，返回的是用户ID+用户名
    return {'uid': userdata.uid, 'username': userdata.username}

# 第2个hook函数用于从 JWT-header 和 JWT-payload 里，获取用户相关的信息
# @jwt.user_lookup_loader
def user_lookup_callback(jwt_header, jwt_data):
    """
    解析JWT时使用.
    此回调函数必须接受2个参数，然后根据这2个参数附带的JWT信息，提取用户信息并返回（可以是任何Python对象）.
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
    print(f"user_identity_loader_callback[mock] -> userdata: {userdata}")
    return userdata

@jwt.user_lookup_loader
def user_lookup_callback_mock(jwt_header, jwt_data):
    userdata = jwt_data["sub"]
    print(f"user_lookup_callback[mock] -> userdata: {userdata}")
    # 这里也直接返回就可以了
    return userdata

# ----------------------- Flask-Principal 的hook函数 ----------------------------
# 注册用户身份加载的函数，有两种使用场景：
# 1. 跨请求保持用户身份：使用某个持久化存储来加载用户身份，此时也需要注册一个对应的 identity_saver 函数实现存入
# 2. REST-API：此时不需要跨请求，但是用户身份需要每次都从 request 的 JWT-Token 里解析
# 这里简单实现了一个REST-API下的跨请求保存用户身份的功能，直接在内存里存放已登录用户的信息，未考虑线程安全 —— 仅供演示
LOGGED_USER = None  # 存放已登录用户的 username，只保存一个，后续登录的会挤掉上一个用户
@principal.identity_loader
def user_identity_loading():
    global LOGGED_USER
    if LOGGED_USER:
        return Identity(id=LOGGED_USER)
    else:  # 没有拿到登录用户时，需要返回None
        return None

@principal.identity_saver
def user_identity_saving(identity: Identity):
    global LOGGED_USER
    if LOGGED_USER is not None:
        current_app.logger.warning(f"user_identity_saving -> Overwrite logged user: {LOGGED_USER}...")
    LOGGED_USER = identity.id
    current_app.logger.debug(f"user_identity_saving -> LOGGED_USER: {LOGGED_USER}...")


@identity_loaded.connect
def principal_identity_loaded(sender, identity: Identity):
    """在这个回调函数里根据用户ID，添加用户的角色"""
    # print(f"principal_identity_loaded: prepare to add roles for {identity}")
    current_app.logger.debug(f"principal_identity_loaded -> prepare to add roles for {identity}.")
    authorized_users = current_app.config['AUTHORIZED_USERS']
    # 这里 identity.id 是 username
    user_config = authorized_users.get(identity.id, {})
    if not user_config:
        return None
    for role in user_config['roles']:
        role_need = RoleNeed(role)
        # print(f"principal_identity_loaded -> RoleNeed '{role_need}' was added to identity: {identity}.")
        current_app.logger.debug(f"principal_identity_loaded -> RoleNeed '{role_need}' is added to identity: {identity}.")
        identity.provides.add(role_need)

# 使用下面这个装饰器从每次请求的JWT里获取用户身份时，需要 Principal 里不设置任何 identity_loader/identity_saver 回调函数
# 也就是禁止使用自动添加的 session 存储，以及注释掉上面使用 LOGGER_USER 的两个回调函数
def principal_jwt_verify(fn):
    """
    Flask-Principle搭配Flask-JWT使用的装饰器，用在 @jwt_required 之后，
    获取JWT解析的用户并设置Principal需要使用的identity.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        current_user = get_current_user()
        if current_user:
            print(f"principal_jwt_verify -> current_user: {current_user}.")
            identity = Identity(id=current_user['username'])
            # 这里通过闭包使用了上面初始化的 Principal 对象，需要注意
            principal.set_identity(identity=identity)
            print(f"principal_jwt_verify -> identity: {identity}.")
        # return current_app.ensure_sync(fn)(*args, **kwargs)
        return fn(*args, **kwargs)
    return wrapper
