from flask import request, current_app, jsonify
from .views1 import *
from extentions import auth, api_abort, generate_token

@bp1.route("/", methods=['GET'])
def hello():
    return "<h1>Hello Flask for Authentication!</h1>"

@bp1.route("/get_token", methods=['POST'])
def get_token():
    # print(request.form)
    grant_type = request.form.get('grant_type')
    user = request.form.get('user')
    passwd = request.form.get('passwd')
    # print(grant_type, user, passwd)
    if grant_type is None or grant_type != 'password':
        return api_abort(code=400, message='The grant type must be password')
    if user is None or passwd is None:
        return api_abort(code=400, message='Empty user or password is forbidden')
    authorized_user = current_app.config['AUTHORIZED_USER']
    user_passwd = authorized_user.get(user, None)
    if user not in authorized_user or passwd != user_passwd:
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

@bp1.route("/test_token", methods=['GET'])
@auth.login_required
def test_token():
    return "<h1>Congratulations for passing token authorization!</h1>"

