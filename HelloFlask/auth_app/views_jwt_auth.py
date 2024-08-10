from flask.blueprints import Blueprint
from flask import request, current_app, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token  # Flask-JWT 自带了token生成的函数，比较方便
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity, get_current_user, current_user
from extensions import db
from auth_app.models import User
from auth_app.exts import api_abort, principal_jwt_verify
from auth_app.principal import Identity, identity_changed, RoleNeed, Permission

# Flask-JWT 扩展研究，它也不需要从 exts.py 里引入 JWTManager 实例对象
jwt_bp = Blueprint('jwt_bp', __name__, url_prefix='/jwt_bp')
# Flask-JWT 使用时，重点关注如下函数：
"""
@jwt_required() 装饰器，保护视图函数，它内部实际是调用 verify_jwt_in_request() 函数执行的操作.
  + optional: True表示允许没有JWT信息的请求访问视图函数，默认False
  + fresh: 
  + refresh: True表示只能允许refresh token访问，False表示允许access token访问，默认 False
  + locations: 设置JWT的解析位置，由 JWT_TOKEN_LOCATION 配置项决定，默认为 headers
create_access_token()/create_refresh_token() 函数, 生成访问/刷新 token, 底层调用的是 PyJWT 库
  + identity: 此token持有的用户身份，可以是任何json序列化的对象，
    后续会被传递给 @jwt.user_identity_loader 和 @jwt.additional_claims_loader 回调函数
  + expires_delta: token过期时间，为 datetime.timedelta 类型，
    分别由 JWT_REFRESH_TOKEN_EXPIRES 和 JWT_ACCESS_TOKEN_EXPIRES 变量配置
  + additional_claims: token的附加信息
get_jwt() 函数，获取解析后JWT的payload，实际是读取 g._jwt_extended_jwt 的值，最重要的函数.
get_jwt_header() 函数，获取解析后JWT的payload，实际是读取 g._jwt_extended_jwt_header 的值.
get_jwt_identity() 函数，获取解析后JWT的identity，实际是读取 g._jwt_extended_jwt['sub'] 的值
get_current_user()函数 / current_user常量，获取JWT里解析的当前用户，实际是读取 g._jwt_extended_jwt_user["loaded_user"] 的值
"""

# ---------------------------------------------------------------------------------------------
# 使用 @jwt_required 装饰器来保护视图函数，它内部的大致逻辑如下：
# 调用 verify_jwt_in_request(), 从请求中解析得到 JWT token, 然后在 flask 的全局变量 g 中存放如下信息（下面是解析失败时的默认值）
#   + g._jwt_extended_jwt_header = {}  # JWT header数据
#   + g._jwt_extended_jwt = {}         # JWT payload，也就是token
#   + g._jwt_extended_jwt_location = None  # JWT 位置
#   + g._jwt_extended_jwt_user = {"loaded_user": None}  # 解析得到的用户
# Flask-JWT提供的一些函数，就是从这些地方获取信息，具体如下：
#  get_jwt()：读取的就是 g._jwt_extended_jwt
#  get_jwt_identity()：先使用 get_jwt() 读取 g._jwt_extended_jwt，
#    然后读取其中的 JWT_IDENTITY_CLAIM 参数设置的key（默认为sub）里
#    存放的内容，实际上就是 @jwt.user_identity_loader 设置的回调函数的返回值
#  get_current_user()：读取 g._jwt_extended_jwt_user，这个属性是一个 {'loaded_user': data} 字典，其中 data 就是
#    @jwt.user_lookup_loader 设置的回调函数的返回值
#  此外 flask_jwt_extended.current_user 常量就是get_current_user()的返回值，只是简单的做了一个lambda调用封装
# ---------------------------------------------------------------------------------------------


@jwt_bp.route("/", methods=['GET'])
def hello():
	return "<h1>Hello Flask for JWT-Extended !</h1>"


# @jwt_bp.route("/login", methods=["POST"])
def login():
	"""根据 用户名+密码，验证用户身份，获取访问接口的token，这是访问数据库的版本"""
	username = request.json.get("username", None)
	password = request.json.get("password", None)
	if username is None or password is None:
		return f"empty username or password is not allowed !", 403
	# 这里复用了 Flask-Login 使用的 User 类
	# 根据用户名查询用户信息
	user = User.query.filter_by(username=username).first()
	if user is None:
		return f"user [{username}] is not found !", 403
	# 验证用户密码
	if user.validate_password(password):
		# 创建token，identity是代表用户身份的参数，这里使用了用户名
		# 自定义的信息可以通过 additional_claims 参数传入
		other_info = {'auth_backend': 'Flask-JWT', 'roles': 'User-Role'}
		# ------------------------------------------------------------------
		# 下面两个方法里identity参数传入的都是 User 对象，实际上 identity参数的值，
		# 会被传递给 @jwt.user_identity_loader 装饰器设置的回调函数作为参数
		# ------------------------------------------------------------------
		# 获取访问接口的 token，这个token的有效时间一般很短
		access_token = create_access_token(identity=user, additional_claims=other_info)
		# 获取刷新token，这个token的使用是可选的，不过JWT认证方案里，一般都会使用两个token
		refresh_token = create_refresh_token(identity=user, additional_claims=other_info)
		return jsonify(access_token=access_token, refresh_token=refresh_token)
	else:
		return f"wrong password!", 403


@jwt_bp.route("/login_mock", methods=["POST"])
def login_mock():
	"""这里是一个不访问数据库的版本，方便快速验证"""
	username = request.json.get("username", None)
	password = request.json.get("password", None)
	if username is None or password is None:
		return api_abort(code=403, message=f"empty username or password is not allowed !")
	# 这里不从数据库查询了
	authorized_users = current_app.config['AUTHORIZED_USERS']
	user_config = authorized_users.get(username, None)
	if user_config is None:
		return api_abort(code=403, message=f"user [{username}] is not found !")
	user_passwd = user_config.get('passwd', None)
	# 验证用户密码
	if password == user_passwd:
		# 这里的identity是一个字典，存放了用户名和角色组
		userdata = {'username': username, 'uid': user_config['uid'], 'roles': user_config['roles']}
		print(f"login[mock] -> identity: {userdata}")
		other_info = {'auth_backend': 'Flask-JWT', 'role_info': 'User-Role'}
		# 下面会调用两次 @jwt.user_identity_loader 设置的回调函数
		access_token = create_access_token(identity=userdata, additional_claims=other_info)
		refresh_token = create_refresh_token(identity=userdata, additional_claims=other_info)
		return jsonify(access_token=access_token, refresh_token=refresh_token)
	else:
		return api_abort(code=403, message="invalid password !")


@jwt_bp.route("/refresh_token", methods=["POST"])
@jwt_required(refresh=True)   # 使用 refresh=True，表示只允许 refresh_token 访问 ----- KEY
def refresh_token():
	"""专门用来刷新 access_token 的接口，这个接口只能通过 refresh_token 来访问"""
	identity = get_jwt_identity()
	# 再次获取附加信息
	# other_info = {'auth_backend': 'Flask-JWT', 'role_info': 'User-Role'}
	jwt_data = get_jwt()
	other_info = {'auth_backend': jwt_data.get('auth_backend', ''), 'role_info': jwt_data.get('role_info', '')}
	access_token = create_access_token(identity=identity, additional_claims=other_info)
	return jsonify(access_token=access_token)


@jwt_bp.route("/current_user", methods=["GET"])
@jwt_required(refresh=False)
def show_current_user():
	# 获取当前用户的信息，也就是 @jwt.user_identity_loader 设置的回调函数返回值
	identity = get_jwt_identity()
	print(f"show_current_user -> identity: {identity}")
	# token里的附加信息通过如下方式获取
	jwt_data = get_jwt()
	other_info = {'auth_backend': jwt_data.get('auth_backend', ''), 'role_info': jwt_data.get('role_info', '')}
	res = {'uid': identity['uid'], 'username': identity['username'], 'other_info': other_info}
	return jsonify(res), 200


# ------------------------------ 配合 Flask-Principal 使用 ---------------------------------
@jwt_bp.route("/principal/login", methods=["POST"])
def principal_login():
	"""登录时设置Flask-Principal的信息"""
	username = request.json.get("username", None)
	password = request.json.get("password", None)
	if username is None or password is None:
		return api_abort(code=403, message=f"empty username or password is not allowed !")
	# 这里不从数据库查询了
	authorized_users = current_app.config['AUTHORIZED_USERS']
	user_config = authorized_users.get(username, None)
	if user_config is None:
		return api_abort(code=403, message=f"user [{username}] is not found !")
	user_passwd = user_config.get('passwd', None)
	# 验证用户密码
	if password == user_passwd:
		# 这里的identity是一个字典，存放了用户名和角色组
		userdata = {'username': username, 'uid': user_config['uid'], 'roles': user_config['roles']}
		print(f"Principal-login -> userdata: {userdata}")
		other_info = {'auth_backend': 'Flask-JWT', 'role_info': 'User-Role'}
		# 下面会调用两次 @jwt.user_identity_loader 设置的回调函数
		access_token = create_access_token(identity=userdata, additional_claims=other_info)
		refresh_token = create_refresh_token(identity=userdata, additional_claims=other_info)
		# --------- 通知Flask-Principal用户身份已变更 ------------
		identity = Identity(id=username, auth_type='Bear-Token')
		print(f"Principal-login -> identity: {identity}")
		identity_changed.send(current_app._get_current_object(), identity=identity)
		# -----------------------------------------------------
		return jsonify(access_token=access_token, refresh_token=refresh_token)
	else:
		return api_abort(code=403, message="invalid password !")

admin_permission = Permission(RoleNeed('admin'))
normal_permission = Permission(RoleNeed('normal'))
role_permission = admin_permission.union(normal_permission)

@jwt_bp.get('/principal/admin')
@jwt_required(refresh=False)
@principal_jwt_verify   # 自定义装饰器
@admin_permission.require(http_exception=403)
def principal_admin_index():
	return "<h1>Only if you are an admin !</h1>"

@jwt_bp.get('/principal/normal')
@jwt_required(refresh=False)
@principal_jwt_verify
@normal_permission.require(http_exception=403)
def principal_normal_index():
	return "<h1>Only if you are a normal user.</h1>"

@jwt_bp.get('/principal/all')
@jwt_required(refresh=False)
@principal_jwt_verify
@role_permission.require(http_exception=403)
def principal_role_index():
	return "<h1>If you are a user...</h1>"
