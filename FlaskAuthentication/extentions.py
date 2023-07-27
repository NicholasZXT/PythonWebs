# 所有扩展的依赖和对象的初始化都放到这里，以便进行模块拆分
import os
from flask import current_app, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPTokenAuth
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired
from werkzeug.http import HTTP_STATUS_CODES

db = SQLAlchemy()
auth = HTTPTokenAuth(scheme='Bearer')

@auth.verify_token
def verify_token(token):
    s = Serializer(secret_key=current_app.config['SECRET_KEY'])
    try:
        data = s.loads(token)
    except (BadSignature, SignatureExpired):
        return False
    user_name = data['user']
    user = current_app.config['AUTHORIZED_USER'].get(user_name, None)
    if user is None:
        return False
    return True

@auth.error_handler
def auth_error(status):
    return "Access Denied", status

def generate_token(user):
    expiration = current_app.config['TOKEN_EXPIRATION']
    s = Serializer(secret_key=current_app.config['SECRET_KEY'], expires_in=expiration)
    token = s.dumps({'user': user}).decode()
    return token, expiration

def api_abort(code, message=None, **kwargs):
    if message is None:
        message = HTTP_STATUS_CODES.get(code, '')
    response = jsonify(code=code, message=message, **kwargs)
    response.status_code = code
    return response