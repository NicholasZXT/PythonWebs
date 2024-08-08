import sys
import logging
from flask import Flask
from configs import config
from extensions import db
from rest_app.views_restful import restful_bp
from rest_app.views_classful import ClassBasedViews
from auth_app.exts import login_manager, jwt, principal
from auth_app.views_rest_auth import auth_bp
from auth_app.views_login_auth import login_bp
from auth_app.views_jwt_auth import jwt_bp
from auth_app.views_principal import principal_bp
from file_app import file_bp


def create_app(config_name: str = 'dev'):
    app = Flask(__name__)
    config_obj = config.get(config_name)
    app.config.from_object(config_obj)
    # ------ 蓝图注册 ---------
    app.register_blueprint(blueprint=auth_bp)
    app.register_blueprint(blueprint=login_bp)
    app.register_blueprint(blueprint=jwt_bp)
    app.register_blueprint(blueprint=restful_bp)
    app.register_blueprint(blueprint=file_bp)
    app.register_blueprint(blueprint=principal_bp)
    # ------ 初始化扩展 ---------
    db.init_app(app)
    app.db = db  # 设置一下，以便在 flask-shell 或者 with app.app_context() 里拿到 db 对象进行调试
    ClassBasedViews.register(app)
    login_manager.init_app(app)
    jwt.init_app(app)
    principal.init_app(app)
    return app


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # 必须要导入表定义才能创建
        from auth_app.models import User
        print("****** creating all tables... ******")
        # db.create_all()
        print("****** creating all tables done. ******")
    print(app.url_map)
    app.logger.setLevel(logging.DEBUG)
    app.run(host='localhost', port=8100)
    # app.run(host='10.8.6.203', port=8100)

