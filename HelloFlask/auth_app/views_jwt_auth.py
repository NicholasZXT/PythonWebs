from flask.blueprints import Blueprint
from flask import request, current_app, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt, get_jwt_identity,  \
	current_user, get_current_user
from extensions import db
from auth_app.models import User

jwt_bp = Blueprint('jwt_bp', __name__)


# @jwt_bp.route("/login", methods=["POST"])
def login():
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
		# 获取访问接口的 token，这个token的有效时间一般很短
		access_token = create_access_token(identity=username, additional_claims=other_info)
		# 获取刷新token，这个token的使用是可选的，不过JWT认证方案里，一般都会使用两个token
		refresh_token = create_refresh_token(identity=username, additional_claims=other_info)
		return jsonify(access_token=access_token, refresh_token=refresh_token)
	else:
		return f"wrong password!", 403


@jwt_bp.route("/login_mock", methods=["POST"])
def login_mock():
	"""这里是一个不访问数据库的版本，方便快速验证"""
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
		access_token = create_access_token(identity=username, additional_claims=other_info)
		refresh_token = create_refresh_token(identity=username, additional_claims=other_info)
		return jsonify(access_token=access_token, refresh_token=refresh_token)
	else:
		return f"wrong password!", 403


# 使用 jwt_required 装饰器来保护视图函数，它内部的大致逻辑如下：
# 从请求中解析得到 JTW token，解析后，会在 flask 的全局变量 g 中存放如下信息（下面是解析失败时的默认值）
#   + g._jwt_extended_jwt = {}  # JWT token的数据
#   + g._jwt_extended_jwt_user = {"loaded_user": None}  # 解析得到的用户
#   + g._jwt_extended_jwt_header = {}
#   + g._jwt_extended_jwt_location = None
# Flask-JWT提供的一些函数，就是从这些地方获取信息，具体如下：
#  get_jwt()：读取的就是 g._jwt_extended_jwt
#  get_jwt_identity()：先使用 get_jwt() 读取 g._jwt_extended_jwt，然后读取其中的
#  get_current_user()：读取 g._jwt_extended_jwt_user 里的 'loaded_user' 内容，此外 current_user 就是它的返回值，只是简单的做了一个lambda调用封装


@jwt_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)   # 使用 refresh=True，表示只允许 refresh_token 访问 ----- KEY
def refresh():
	"""专门用来刷新 access_token 的接口，这个接口只能通过 refresh_token 来访问"""
	identity = get_jwt_identity()
	# TODO 如何再次获取这个附加信息呢？
	other_info = {'auth_backend': 'Flask-JWT'}
	access_token = create_access_token(identity=identity, additional_claims=other_info)
	return jsonify(access_token=access_token)


# 使用 jwt_required 装饰器 来保护需要使用JWT认证的视图函数，jwt_required有如下参数
#   + locations=[]，用于指定从请求中的哪个位置获取JWT信息
@jwt_bp.route("/current_user", methods=["GET"])
@jwt_required()
def protected_view():
	# Access the identity of the current user with get_jwt_identity
	current_user = get_jwt_identity()
	# token里的附加信息通过如下方式获取
	other_info = get_jwt()
	res = {'uid': current_user.uid, 'username': current_user.username, 'other_info': other_info}
	return jsonify(res), 200


@jwt_bp.route("/current_user_mock", methods=["GET"])
@jwt_required()
def protected_view_mock():
	"""这里是一个不访问数据库的版本，方便快速验证"""
	current_user = get_jwt_identity()
	# token里的附加信息通过如下方式获取
	other_info = get_jwt()
	res = {'uid': current_user['uid'], 'username': current_user['username'], 'other_info': other_info}
	return jsonify(res), 200
