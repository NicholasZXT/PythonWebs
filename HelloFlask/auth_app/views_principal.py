from flask.blueprints import Blueprint
from flask import request, current_app, g, jsonify
from werkzeug.http import HTTP_STATUS_CODES
from functools import partial
from collections import namedtuple
# from flask_principal import RoleNeed, UserNeed, ItemNeed, Permission, identity_changed, identity_loaded, Identity, AnonymousIdentity
from auth_app.principal import RoleNeed, UserNeed, ItemNeed, Permission, identity_changed, identity_loaded, Identity, AnonymousIdentity
from auth_app.exts import api_abort

# Flask-Principal 扩展研究，详细说明见拷贝出来的 principal.py 源码文件
principal_bp = Blueprint('principal_bp', __name__, url_prefix='/principal_bp')

@principal_bp.get('/')
def principal_hello():
	return "<h1>Hello Flask-Principal !</h1>", 200

# 不同的权限对应于不同的 Permission 对象，如果要对各种权限进行组合，Permission 对象也提供了类似集合的交并差补方法来创建新的权限集合
admin_permission = Permission(RoleNeed('admin'))
normal_permission = Permission(RoleNeed('normal'))
role_permission = admin_permission.union(normal_permission)

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
	# 一旦上面验证过用户的身份，就需要开发者手动创建一个该用户对应的 Identity 对象，auth_type参数用于记录身份校验的方式，传不传没啥影响
	identity = Identity(id=username, auth_type='Bear-Token')
	# uid = user_config['uid']
	# identity = Identity(id=uid, auth_type='Bear-Token')
	current_app.logger.info(f"principal_login: sending signal to identity_changed with identity: {identity}...")
	# 然后调用 Flask-Principal 提供的 identity_changed 信号量的 send 方法，传入当前用户的身份标识 Identity，以便其它组件获取用户身份
	identity_changed.send(current_app._get_current_object(), identity=identity)
	return "<h1>Login Successfully</h1>", 200

# 在需要保护的视图函数前，调用待校验的权限对象Permission的require装饰器，表示所有访问该视图函数的请求，都要经过此Permission的校验
@principal_bp.get('/hello/admin')
@admin_permission.require(http_exception=403)  # 权限校验失败时的HTTP错误码
def admin_index():
	return "<h1>Only if you are an admin !</h1>"

@principal_bp.get('/hello/normal')
@normal_permission.require(http_exception=403)  # 权限校验失败时的HTTP错误码
def normal_index():
	return "<h1>Only if you are a normal user.</h1>"

@principal_bp.get('/hello/all')
@role_permission.require(http_exception=403)  # 权限校验失败时的HTTP错误码
def role_index():
	return "<h1>If you are a user...</h1>"

@principal_bp.post('/logout')
@role_permission.require(http_exception=403)
def principal_logout():
	username = request.json.get('username')
	authorized_users = current_app.config['AUTHORIZED_USERS']
	if username not in authorized_users:
		return api_abort(code=400, message='Invalid username')
	current_app.logger.info(f"Username: {username} is LOGOUT successfully ...")
	# 用户登出时，也需要调用 identity_changed 信号量的 send() 方法，将用户切换成匿名用户身份标识 ------------------ KEY
	identity_changed.send(current_app._get_current_object(), identity=AnonymousIdentity())
	return "<h1>Logout Successfully</h1>", 200

# 上面的实践可以看出，对于web token认证方式，不使用 session + 不借助存储系统 的情况下，不太容易实现跨请求保持用户身份。
# 因为token认证过程中，用户的身份信息都在每次请求的token中，Flask-HttpAuth的 HTTPTokenAuth.login_required 装饰器会在 每次请求进入视图
# 函数前进行token的解析和身份认证（HTTPTokenAuth.verity_token回调函数），并将通过认证的用户信息存放在 g.flask_httpauth_user 中。
# 但问题是，Principal 对象在整个app上注册了一个 before_request 回调函数：Principal._on_before_request，这个回调函数是在上面的
# token解析过程之前进行的，此时就没办法获取到token里的用户身份，如果此时没有定义自己的identity_loader，那么 Principal._on_before_request
# 就会一直将 g.identity 设置成 AnonymousIdentity，导致后面一直无法通过校验。
# 似乎一个解决办法是使用 @Principal.identity_loader 定义一个回调函数，在里面实现和HTTPTokenAuth.verity_token回调函数里同样的逻辑。

# Flask-Security的做法似乎就是上面那样，它在 init_app() 方法里实例化 Principal 的时候：
# 注册了一个 identity_loader 回调函数 _identity_loader()，该函数里面调用 Flask-Login 的代理对象current_user
# --> 代理对象current_user 里面调用 login_manager._load_user() 方法获取用户
# --> 调用login_manager._load_user_from_request, 这个方法是 Flask-Security设置的回调函数 _request_loader()
# --> _request_loader()方法里，似乎是从请求头的token里解析用户，然后查询数据库用户的token信息？
# 个人感觉 Flask-Security 对于 Flask-Login 的依赖过于深了。
# 此外 Flask-Security 在 init_app() 方法里，还向 Principal 的 identity_loaded 信号量 connect() 了一个回调函数:
# _on_identity_loaded，该回调函数用于根据 Identity 身份从数据库里查询对于的权限并进行配置。


# ---------------------------- 细粒度的权限校验使用示例 ----------------------------
# 示例来自Flask-Principal的 Granular Resource Protection 小节
# 如果需要控制只有admin角色的用户，能编辑自己创建的文章，那么可以按照如下方式拆分权限：
# 1. 要求有效用户，那么任意一个成功加载的 Identity对象 均表示有效的用户信息
# 2. 要求admin角色，那么就在Identity中加入 RoleNeed('admin')，表示该Identity属于admin角色
# 3. 只有用户本身能编辑，那么就创建一个对应的 ItemNeed，里面记录为 ('update', 'article-1', 'article')，
#    表示该Identity拥有 update 对象article 里 article-1 的文章的权限
# 然后构建一个Permission对象，在视图函数里初始化时持有一个当前用户的 ItemNeed('update', 'article-1', 'article')，然后进行权限校验
# ----------------
# 下面定义一个表示只能文章创建者能进行 read/update 的 Need 对象
# 使用partial封装一个 ItemNeed 对象，固定 method, type 参数，只剩 value 参数需要设置
# ArticleUpdateNeed = partial(ItemNeed, method='update', type='Article')
# a1 = ArticleUpdateNeed(value='article-1')
# print(a1)
# 上面由于ItemNeed的字段定义顺序原因，只能使用关键字参数来固定参数，为了方便使用，可以自己重新定义一个
# 下面的 type 其实可以省略，因为名称就指定了是 Article，另外 value 字段表示的是文章的ID
ArticleNeed = namedtuple('ArticleNeed', ['type', 'method', 'value'])
ArticleReadNeed = partial(ArticleNeed, 'Article', 'read')  # 固定前两个参数
ArticleUpdateNeed = partial(ArticleNeed, 'Article', 'update')  # 固定前两个参数
# a2 = ArticleReadNeed('article-2')   # 这里就可以省略参数名了
# print(a2)
# t1 = {
# 	ArticleNeed(type='Article', method='update', value=1),
# 	ArticleNeed(type='Article', method='update', value=2),
# 	ArticleNeed(type='Article', method='update', value=3)
# }
# t2 = {ArticleNeed(type='Article', method='update', value=1)}
# t1.intersection(t2)
# t2.intersection(t1)
# ---------------
# 模拟数据
UserArticleMockData = [
	# admin用户
	{'uid': 1, 'username': 'admin', 'aid': 1, 'content': 'admin-article-1'},
	{'uid': 1, 'username': 'admin', 'aid': 2, 'content': 'admin-article-2'},
	{'uid': 1, 'username': 'admin', 'aid': 3, 'content': 'admin-article-3'},
	# yourself用户
	{'uid': 2, 'username': 'yourself', 'aid': 4, 'content': 'yourself-article-4'},
	{'uid': 2, 'username': 'yourself', 'aid': 5, 'content': 'yourself-article-5'},
	{'uid': 2, 'username': 'yourself', 'aid': 6, 'content': 'yourself-article-6'}
]
# 首先考虑定义用户的权限，这个操作一般在用户加载时进行，也就是 @identity_loaded.connect 注册的回调函数中进行
@identity_loaded.connect
def load_identity_needs(sender, identity: Identity):
	# 在 exts.py 里已经注册了一个加载用户 Role 的回调函数，所以这里只需要加载用户的 细粒度权限
	# 这里省略了从数据库查询获取当前用户的 article-id 列表的过程，直接从Mock数据中获取
	for article in UserArticleMockData:
		if article['username'] == identity.id:
			# 增加阅读/编辑自己文章的权限
			identity.provides.add(ArticleReadNeed(article['aid']))
			identity.provides.add(ArticleUpdateNeed(article['aid']))

# 然后在视图函数中定义Permission，进行校验
@principal_bp.get('/article/list')
@role_permission.require(http_exception=403)
def read_article():
	result = {}
	# 获取当前用户
	identity = g.identity
	current_app.logger.info(f"read_article -> user[{identity.id}] access...")
	result['username'] = identity.id
	result['data'] = []
	for article in UserArticleMockData:
		if article['username'] == identity.id:
			result['data'].append(article['content'])
	return jsonify(result)

@principal_bp.post('/article/update/<article_id>')
@role_permission.require(http_exception=403)  # 这里先校验 role 权限，下面再校验细粒度权限
def update_article(article_id):
	content = request.json.get('content', '')
	# article_id 必须要转成整数，否则校验的时候会有问题
	article_id = int(article_id)
	# 初始化一个Permission，并传入需要校验的Need，这里不需要校验 role_permission，上面的装饰器里已经校验过了
	# permission = Permission(ArticleUpdateNeed(article_id)).union(role_permission)
	permission = Permission(ArticleUpdateNeed(article_id))
	# 调试语句
	# identity = g.identity
	# current_app.logger.info(f"update_article -> identity to check: {identity}.")
	# current_app.logger.info(f"update_article -> permission to check: {permission}.")
	# print('permission.allows(identity): ', permission.allows(identity))
	# permission.allows(identity)
	# 然后使用 permission.can() 方法进行细粒度的权限校验
	if permission.can():
		return f"you can update article[{article_id}] with new content: {content}."
	return api_abort(403, message=f"you are not allowed to update article[{article_id}]...")  # HTTP Forbidden

