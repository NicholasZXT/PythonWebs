from flask.blueprints import Blueprint
from flask import request, current_app, jsonify
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired
from werkzeug.http import HTTP_STATUS_CODES
from auth_app.exts import auth, generate_token, api_abort

auth_bp = Blueprint('auth', __name__, url_prefix='/auth_bp')


@auth_bp.route("/", methods=['GET'])
def hello():
    return "<h1>Hello Flask for Authentication!</h1>"

@auth_bp.route("/get_token", methods=['POST'])
def get_token():
    """生成Token的视图函数"""
    # print(request.form)
    grant_type = request.form.get('grant_type')
    user = request.form.get('user')
    passwd = request.form.get('passwd')
    # print(grant_type, user, passwd)
    if grant_type is None or grant_type != 'password':
        return api_abort(code=400, message='The grant type must be password')
    if user is None or passwd is None:
        return api_abort(code=400, message='Empty user or password is forbidden')
    authorized_users = current_app.config['AUTHORIZED_USERS']
    user_config = authorized_users.get(user, {})
    user_passwd = user_config.get('passwd', '')
    if user not in authorized_users or passwd != user_passwd:
        return api_abort(code=400, message='Invalid user or password')
    token, expiration = generate_token(user)
    response = jsonify({
        'access_token': token,
        'token_type': 'Bearer',
        'expires_in': expiration
    })
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Pragma'] = 'no-cache'
    return response
    # return "<h1>get_token</h1>"

@auth_bp.route("/test_token", methods=['GET'])
@auth.login_required(role=['admin', 'others'])
def test_token():
    # auth.current_user() 的返回值就是 @auth.verify_token 装饰的函数返回值
    print(f"test_token current user: {auth.current_user()}")
    return "<h1>Congratulations for passing token authorization!</h1>"

@auth_bp.route("/test_admin_token", methods=['GET'])
@auth.login_required(role='admin')
def test_admin_token():
    print(f"test_admin_token current user: {auth.current_user()}")
    return "<h1>Congratulations for passing Administration token authorization!</h1>"

@auth_bp.route("/verify_token", methods=['GET'])
@auth.login_required(role=['admin', 'others'])
def verify_token():
    """
    提供一个验证token是否有效的接口。
    token有效则返回token对应用户的 name 和 roles，否则返回空dict.
    另外还限制此接口只能通过 localhost 来访问 —— 不过这个在使用Nginx做反向代理的情况下，还需做如下配置Nginx传递客户端的真实IP地址：
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header REMOTE-HOST $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    :return:
    """
    current_user = auth.current_user()
    print(f"verify_token current user: {current_user}")
    # 检查当前请求的源主机地址
    access_url = request.url
    remote_addr = request.remote_addr
    remote_host = remote_addr.split(':')[0]
    print(f"verify_token request remote_addr host: {remote_host}")
    # 使用Nginx做反向代理时，只有这个能拿到代理前的源主机IP地址
    forwarded = request.headers.get('x-forwarded-for', None)
    print(f"verify_token request remote x-forwarded-for host: {forwarded}")
    # if forwarded in {'localhost', '127.0.0.1'}:
    if remote_host in {'localhost', '127.0.0.1'}:
        return jsonify(current_user)
    else:
        code = 403
        response = jsonify(code=code, message=HTTP_STATUS_CODES.get(code), detail='Access is forbidden from remote host')
        response.status_code = code
        return response