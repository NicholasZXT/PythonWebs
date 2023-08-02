from flask.blueprints import Blueprint
from flask import request, current_app, jsonify, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from FlaskAuthentication.models.users import User
from FlaskAuthentication.extentions import db
from werkzeug.http import HTTP_STATUS_CODES

login_bp = Blueprint('login_bp', __name__)


@login_bp.route('/in', methods=['GET'])
def home():
    return redirect(location=url_for('login_bp.to_login'), code=302, Response=None)

@login_bp.route('/login_home', methods=['GET'])
def to_login():
    return "<h1>Please login</h1>"

@login_bp.route('/register', methods=['POST'])
def user_register():
    username = request.form.get('username', None)
    password = request.form.get('password', None)
    if username is None or password is None:
        return f"empty username or password is not allowed !", 403
    user_exist = User.query.filter_by(username=username).count()
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
    if user is None:
        return f"user [{username}] is not found !", 403
    if user.validate_password(password):
        # return f"user [{username}] login successfully, you can access /login_welcome page", 200
        return redirect(location=url_for('login_bp.login_welcome_page'))
    else:
        return f"wrong password!", 403


@login_bp.route("/login_welcome")
@login_required
def login_welcome_page():
    return f"user [{current_user.username}] login successfully"


@login_bp.route('/logout', methods=['GET'])
@login_required
def user_logout():
    logout_user()
    flash(message='Logout success.', category='info')
    return redirect(location=url_for('to_login'))