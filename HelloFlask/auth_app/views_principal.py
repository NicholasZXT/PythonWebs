from flask.blueprints import Blueprint
from flask import request, current_app, jsonify
from werkzeug.http import HTTP_STATUS_CODES
from auth_app.exts import auth, generate_token, api_abort
from functools import partial
from collections import namedtuple

# from flask_principal import RoleNeed, ItemNeed, Permission, identity_changed
from .principal import RoleNeed, UserNeed, ItemNeed, Permission, identity_changed, identity_loaded, Identity, AnonymousIdentity


principal_bp = Blueprint('principal_bp', __name__, url_prefix='/principal_bp')

# 设置一个需要用户含有 admin 角色的权限
admin_permission = Permission(RoleNeed('admin'))

# 这里使用 HttpAuth 来做token登录，下面的函数和 views_rest_auth.py 里的 get_token 一样
@principal_bp.post('/login')
def principal_login():
	username = request.json.get('username')
	password = request.json.get('password')
	authorized_users = current_app.config['AUTHORIZED_USERS']
	user_config = authorized_users.get(username, {})
	user_passwd = user_config.get('passwd', '')
	if username not in authorized_users or password != user_passwd:
		return api_abort(code=400, message='Invalid user or password')
	current_app.logger.info(f"principal_login: Username: {username} is LOGIN successfully ...")
	identity = Identity(id=username)
	current_app.logger.info(f"principal_login: sending signal to identity_changed with identity: {identity}...")
	identity_changed.send(current_app._get_current_object(), identity=identity)
	return "<h1>Login Successfully</h1>", 200


@principal_bp.get('/protected_view')
@admin_permission.require(http_exception=403)
def admin_index():
	return "<h1>Only if you are an admin</h1>"


@principal_bp.post('/logout')
@admin_permission.require()
def principal_logout():
	username = request.json.get('username')
	password = request.json.get('password')
	authorized_users = current_app.config['AUTHORIZED_USERS']
	user_config = authorized_users.get(username, {})
	user_passwd = user_config.get('passwd', '')
	if username not in authorized_users or password != user_passwd:
		return api_abort(code=400, message='Invalid user or password')
	current_app.logger.info(f"Username: {username} is LOGOUT successfully ...")
	identity_changed.send(current_app._get_current_object(), identity=AnonymousIdentity())
	return "<h1>Logout Successfully</h1>", 200

# 上面的实践可以看出，对于web token认证方式，不使用 session + 不借助存储系统 的情况下，不太容易实现跨请求保持用户身份。
# 因为token认证过程中，用户的身份信息都在每次请求的token中，Flask-HttpAuth的 HTTPTokenAuth.login_required 装饰器会在 每次请求进入视图
# 函数前进行token的解析和身份认证（HTTPTokenAuth.verity_token回调函数），并将通过认证的用户信息存放在 g.flask_httpauth_user 中。
# 但问题是，Principal 对象在整个app上注册了一个 before_request 回调函数：Principal._on_before_request，这个回调函数是在上面的
# token解析过程之前进行的，此时就没办法获取到token里的用户身份，如果此时没有定义自己的identity_loader，那么 Principal._on_before_request
# 就会一直将 g.identity 设置成 AnonymousIdentity，导致后面一直无法通过校验。
# 似乎一个解决办法是使用 @Principal.identity_loader 定义一个回调函数，在里面实现和HTTPTokenAuth.verity_token回调函数里同样的逻辑。

# Flask-Security的做法似乎就是上面那样，它实例化 Principal 的时候：
# 注册了一个 identity_loader 回调函数 _identity_loader()，该函数里面调用 Flask-Login 的代理对象current_user
# --> 代理对象current_user 里面调用 login_manager._load_user() 方法获取用户
# --> 调用login_manager._load_user_from_request, 这个方法是 Flask-Security设置的回调函数 _request_loader()
# --> _request_loader()方法里，似乎是从请求头的token里解析用户，然后查询数据库用户的token信息？
# 个人感觉 Flask-Security 对于 Flask-Login 的依赖过于深了。


# ---------------------------- 细粒度的权限校验使用示例 ----------------------------
# 示例来自Flask-Principal的 Granular Resource Protection 小节
# 如果需要控制只有admin角色的用户，能编辑自己创建的文章，那么可以按照如下方式拆分权限：
# 1. 要求有效用户，那么就在Identity中加入一个 UserNeed(id='uid-1')，表示有效的用户信息
# 1. 要求admin角色，那么就在Identity中加入 RoleNeed('admin')，表示该Identity属于admin角色
# 3. 只有用户本身能编辑，那么就创建一个对应的 ItemNeed，里面记录为 ('update', 'article-1', 'article')，
#    表示该Identity拥有 update 对象article 里 article-1 的文章的权限
# 然后构建一个Permission对象，在视图函数里初始化时持有一个当前用户的 ItemNeed('update', 'article-1', 'article')，然后进行权限校验

# ----------------
# 下面先定义一个表示只能文章创建者能进行 update 的 Need 对象
# 使用partial封装一个 ItemNeed 对象，固定 method, type 参数，只剩 value 参数需要设置
# ArticleEditNeed = partial(ItemNeed, method='update', type='Article')
# a1 = ArticleEditNeed(value='article-1')
# print(a1)
# 上面由于ItemNeed的字段定义顺序原因，只能使用关键字参数来固定参数，为了方便使用，可以自己重新定义一个
# 下面的 type 其实可以省略，因为名称就指定了是 Article，另外 value 字段表示的是文章的ID
ArticleNeed = namedtuple('ArticleNeed', ['type', 'method', 'value'])
ArticleUpdateNeed = partial(ArticleNeed, 'Article', 'update')  # 固定前两个参数
# a2 = ArticleUpdateNeed('article-2')   # 这里就可以省略参数名了
# print(a2)
# ---------------

# 首先考虑定义用户的权限，这个操作一般在用户加载时进行，也就是 @identity_loaded.connect 注册的回调函数中进行
# @identity_loaded.connect
def load_identity_needs(sender, identity: Identity):
	# 这里省略了获取用户所属的角色和获取当前用户的 article-id 列表的过程
	# 1. 给 identity 增加 admin 角色
	identity.provides.add(RoleNeed('admin'))
	# 2. 给 identity 增加 当前用户信息 这一权限
	identity.provides.add(UserNeed(identity.id))
	# 3. 增加编辑自己文章的权限，这里其实应该是一系列的 ArticleUpdateNeed
	identity.provides.add(ArticleUpdateNeed('article-id'))

# 然后在视图函数中定义Permission，进行校验
# @principal_bp.post('/posts/<article_id>')
def edit_article(article_id):
	# 这里省略了获取当前用户和用户角色的过程
	# 初始化一个Permission，并传入需要校验的Need
	permission = Permission([RoleNeed('admin'), UserNeed('current-user-id'), ArticleUpdateNeed(article_id)])
	# 然后使用 permission.can() 方法进行细粒度的权限校验
	if permission.can():
		return "check passed", 200
	api_abort(403)  # HTTP Forbidden

