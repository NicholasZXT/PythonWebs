from flask.blueprints import Blueprint
from flask import request, current_app, jsonify
from werkzeug.http import HTTP_STATUS_CODES
from auth_app.exts import auth, generate_token, api_abort

# from flask_principal import RoleNeed, ItemNeed, Permission, identity_changed
from .principal import RoleNeed, ItemNeed, Permission, identity_changed, Identity, AnonymousIdentity

principal_bp = Blueprint('principal', __name__, url_prefix='/principal_bp')

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
