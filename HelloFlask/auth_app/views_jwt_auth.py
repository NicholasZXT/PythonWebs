from flask.blueprints import Blueprint
from flask import request, current_app, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt, get_jwt_identity,  \
	get_current_user, current_user
from extensions import db
from auth_app.models import User

jwt_bp = Blueprint('jwt_bp', __name__, url_prefix='/jwt_bp')


@jwt_bp.route("/", methods=['GET'])
def hello():
	return "<h1>Hello Flask for JWT-Extended !</h1>"


# @jwt_bp.route("/login", methods=["POST"])
def login():
	"""
	根据 用户名+密码，验证用户身份，获取访问接口的token
	"""
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
		other_info = {'auth_backend': 'Flask-JWT'}
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
	"""
	这里是一个不访问数据库的版本，方便快速验证
	"""
	username = request.json.get("username", None)
	password = request.json.get("password", None)
	if username is None or password is None:
		return f"empty username or password is not allowed !", 403
	# 这里不从数据库查询了
	authorized_users = current_app.config['AUTHORIZED_USERS']
	user_config = authorized_users.get(username, None)
	user_passwd = user_config.get('passwd', '')
	if user_config is None:
		return f"user [{username}] is not found !", 403
	# 验证用户密码
	if password == user_passwd:
		other_info = {'auth_backend': 'Flask-JWT'}
		# 这里的identity是一个字典，存放了用户名和角色组
		userdata = {'username': username, 'uid': user_config['uid'], 'roles': user_config['roles']}
		print(f"login[mock] - identity: {userdata}")
		access_token = create_access_token(identity=userdata, additional_claims=other_info)
		refresh_token = create_refresh_token(identity=userdata, additional_claims=other_info)
		return jsonify(access_token=access_token, refresh_token=refresh_token)
	else:
		return f"wrong password!", 403


@jwt_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)   # 使用 refresh=True，表示只允许 refresh_token 访问 ----- KEY
def refresh():
	"""专门用来刷新 access_token 的接口，这个接口只能通过 refresh_token 来访问"""
	identity = get_jwt_identity()
	# 再次获取附加信息
	# other_info = get_jwt()
	other_info = {'auth_backend': 'Flask-JWT'}
	access_token = create_access_token(identity=identity, additional_claims=other_info)
	return jsonify(access_token=access_token)

# ---------------------------------------------------------------------------------------------
# 使用 jwt_required 装饰器来保护视图函数，它内部的大致逻辑如下：
# 从请求中解析得到 JTW token，解析后，会在 flask 的全局变量 g 中存放如下信息（下面是解析失败时的默认值）
#   + g._jwt_extended_jwt = {}  # JWT token的数据
#   + g._jwt_extended_jwt_user = {"loaded_user": None}  # 解析得到的用户
#   + g._jwt_extended_jwt_header = {}
#   + g._jwt_extended_jwt_location = None
# Flask-JWT提供的一些函数，就是从这些地方获取信息，具体如下：
#  get_jwt()：读取的就是 g._jwt_extended_jwt
#  get_jwt_identity()：先使用 get_jwt() 读取 g._jwt_extended_jwt，然后读取其中的 JWT_IDENTITY_CLAIM 参数设置的key（默认为sub）里
# 	 存放的内容，实际上就是 @jwt.user_identity_loader 设置的回调函数的返回值
#  get_current_user()：读取 g._jwt_extended_jwt_user，这个属性是一个 {'loaded_user': data} 字典，其中 data 就是
#    @jwt.user_lookup_loader 设置的回调函数的返回值
#  此外 flask_jwt_extended.current_user 常量就是get_current_user()的返回值，只是简单的做了一个lambda调用封装
# ---------------------------------------------------------------------------------------------

# 使用 jwt_required 装饰器 来保护需要使用JWT认证的视图函数，jwt_required有如下参数
#   + locations=[]，用于指定从请求中的哪个位置获取JWT信息
# @jwt_bp.route("/current_user", methods=["GET"])
# @jwt_required()
def protected_view():
	# 获取当前用户的信息，也就是  @jwt.user_identity_loader 设置的回调函数返回值
	identity = get_jwt_identity()
	# token里的附加信息通过如下方式获取
	other_info = get_jwt()
	res = {'uid': identity['uid'], 'username': identity['username'], 'other_info': other_info}
	return jsonify(res), 200


@jwt_bp.route("/current_user_mock", methods=["GET"])
@jwt_required()
def protected_view_mock():
	"""这里是一个不访问数据库的版本，方便快速验证"""
	identity = get_jwt_identity()
	print(f"protected_view[mock] - identity: {identity}")
	# token里的附加信息通过如下方式获取
	other_info = get_jwt()
	res = {'uid': identity['uid'], 'username': identity['username'], 'other_info': other_info}
	return jsonify(res), 200
