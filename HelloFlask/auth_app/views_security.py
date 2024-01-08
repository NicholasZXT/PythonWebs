from werkzeug.http import HTTP_STATUS_CODES
from flask.blueprints import Blueprint
from flask import request, current_app, jsonify
from flask_security.decorators import http_auth_required, auth_required, auth_token_required, roles_required\
    , roles_accepted, permissions_accepted, permissions_required, current_user

security_bp = Blueprint('security_bp', __name__, url_prefix='/security_bp')

"""
Flask-Security在结合到视图函数时，主要使用 decorators.py 中提供的如下装饰器：
+ http_auth_required(realm)：使用Basic HTTP authentication进行认证
  + realm: 
+ auth_token_required()：使用 token authentication 进行认证
+ auth_required(*auth_methods, within=-1, grace=None)：使用多个方式进行认证
  + auth_methods: 一个或者多个认证机制，可以从 (token, basic, session) 中选
+ roles_required(*roles)：当前用户必须要满足 所有 列出的role 才能访问视图函数
  + roles: 角色列表，每个角色由字符串表示
+ roles_accepted(*roles)：当前用户只需要满足 至少一个 列出的role 才能访问视图函数
+ permissions_required：当前用户必须要满足 所有 列出的permission 才能访问视图函数
+ permissions_accepted：当前用户只需要满足 至少一个 列出的permission 才能访问视图函数
+ anonymous_user_required
"""

@security_bp.get('/')
def security_hello():
    return "<h1>Hello Flask-Security !</h1>"


