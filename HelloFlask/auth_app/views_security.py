from werkzeug.http import HTTP_STATUS_CODES
from flask.blueprints import Blueprint
from flask import request, current_app, jsonify
from flask_security.decorators import http_auth_required, auth_required, auth_token_required
from flask_security.decorators import roles_required, roles_accepted, permissions_accepted, permissions_required

#  Flask-Security 扩展研究
security_bp = Blueprint('security_bp', __name__, url_prefix='/security_bp')

"""
Flask-Security在结合到视图函数时，主要使用 decorators.py 中提供的如下装饰器：
用于身份认证（authentication）
+ http_auth_required(realm)：使用Basic HTTP authentication进行认证
  + realm: 
+ auth_token_required()：使用 token authentication 进行认证
+ auth_required(*auth_methods, within=-1, grace=None)：使用多个方式进行认证
  + auth_methods: 一个或者多个认证机制，可以从 (token, basic, session) 中选
用于权限鉴别（authorization）
+ roles_required(*roles)：当前用户必须要满足 所有 列出的role 才能访问视图函数
  + roles: 角色列表，每个角色由字符串表示
+ roles_accepted(*roles)：当前用户只需要满足 至少一个 列出的role 才能访问视图函数
+ permissions_required：当前用户必须要满足 所有 列出的permission 才能访问视图函数
+ permissions_accepted：当前用户只需要满足 至少一个 列出的permission 才能访问视图函数
+ anonymous_user_required

如果实例化Security对象时，使用register_blueprint=False参数禁止了自动生成的蓝图，那么对于User和Role的CRUD操作，也需要用户自己定义对应的
视图函数，在这些视图函数里 Security.datastore 提供的各种方法对 User+Role 进行CRUD操作。
"""

@security_bp.get('/')
def security_hello():
    return "<h1>Hello Flask-Security !</h1>"

# TODO 待深入研究使用
