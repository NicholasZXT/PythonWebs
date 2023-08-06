# 所有扩展的依赖和对象的初始化都放到这里，以便进行模块拆分
import os
from flask import current_app, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPTokenAuth
# itsdangerous 的 TimedJSONWebSignatureSerializer 只在 2.0.1 及其之前的版本中有，2.x 开始的官方文档建议转向 authlib
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired
from flask_login import LoginManager

db = SQLAlchemy()

# Web应用的用户认证
login_manager = LoginManager()

# Web-API的接口认证
auth = HTTPTokenAuth(scheme='Bearer')

@auth.verify_token
def verify_token(token):
    s = Serializer(secret_key=current_app.config['SECRET_KEY'])
    try:
        data = s.loads(token)
    except (BadSignature, SignatureExpired):
        return False
    user_name = data['user']
    user = current_app.config['AUTHORIZED_USER'].get(user_name, None)
    if user is None:
        return False
    return True

@auth.error_handler
def auth_error(status):
    return "Access Denied", status

# 在 login_manager 中注册一个 user_loader 函数，用于配合 Flask-login 提供的 current_user 使用
# 如果用户已登录，current_user 会调用此处返回加载的 User 类对象；
# 如果用户未登录，则返回 Flask-login 内置的 AnonymousUserMixin 类对象
@login_manager.user_loader
def load_user(uid):
    from FlaskAuthentication.models import User
    user = User.query.get(int(uid))
    print(f"@login_manager.user_loader get user [id={uid}, username={user.username}].")
    return user

# 设置访问需要登录资源时，自动跳转的登录视图的端点值（包括蓝本名称的完整形式）
# 如果不设置这个，访问需要登录的资源时，会返回 401 Unauthorized 的简单HTML页面
login_manager.login_view = "login_bp.to_login"