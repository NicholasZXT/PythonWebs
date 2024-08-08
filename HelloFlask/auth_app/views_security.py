from werkzeug.http import HTTP_STATUS_CODES
from flask.blueprints import Blueprint
from flask import request, current_app, jsonify
from flask_security import Security
from flask_security.decorators import http_auth_required, auth_required, auth_token_required
from flask_security.decorators import roles_required, roles_accepted, permissions_accepted, permissions_required
from auth_app.models import user_datastore

# Flask-Security扩展研究
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


# --------------------------------------------------------------------------------
#  Flask-Security 蓝图
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
