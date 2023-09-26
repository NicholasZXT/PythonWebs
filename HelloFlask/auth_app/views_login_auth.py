from werkzeug.http import HTTP_STATUS_CODES
from flask.blueprints import Blueprint
from flask import request, current_app, jsonify, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from auth_app.models import User
from auth_app.exts import db

login_bp = Blueprint('login_bp', __name__)


@login_bp.route('/in', methods=['GET'])
def home():
    return redirect(location=url_for('login_bp.to_login'), code=302, Response=None)

@login_bp.route('/login_home', methods=['GET'])
def to_login():
    # 用这个来代替填写登录信息表单的HTML页面
    return "<h1>Please login</h1>"

@login_bp.route('/register', methods=['POST'])
def user_register():
    username = request.form.get('username', None)
    password = request.form.get('password', None)
    if username is None or password is None:
        return f"empty username or password is not allowed !", 403
    user_exist = User.query.filter_by(username=username).count()
    # user_exist = db.session.execute(db.select(User).filter_by(username=username)).scalar_one()
    print('user_exist: ', user_exist)
    if user_exist > 0:
        return f"failed to create new user [{username}] due to exist !", 403
    else:
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        return f"new user[{username}] is created successfully !", 200


@login_bp.route('/login', methods=['POST'])
def user_login():
    username = request.form.get('username', None)
    password = request.form.get('password', None)
    if username is None or password is None:
        return f"empty username or password is not allowed !", 403
    user = User.query.filter_by(username=username).first()
    # user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one()
    if user is None:
        return f"user [{username}] is not found !", 403
    if user.validate_password(password):
        # 登录当前用户
        login_user(user)
        # return f"user [{username}] login successfully, you can access /login_welcome page", 200
        return redirect(location=url_for('login_bp.login_welcome_page'))
    else:
        return f"wrong password!", 403


@login_bp.route("/login_welcome", methods=['GET'])
@login_required
def login_welcome_page():
    return f"user [{current_user.username}] login successfully"


@login_bp.route('/logout', methods=['GET'])
@login_required
def user_logout():
    print('<user_logout>-current_user: ', current_user)
    # 只有在 登出之前，才能获取到 username
    username = current_user.username
    logout_user()
    # 登出用户之后，current_user 就改变了
    print('<user_logout>-AnonymousUserMixin: ', current_user)
    flash(message=f'user [{username}] logout success.', category='info')
    return redirect(location=url_for('login_bp.to_login'))