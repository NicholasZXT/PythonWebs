from flask import Flask
from configs import config
from extensions import db
from auth_app.exts import auth, login_manager
from auth_app.views_rest_auth import auth_bp
from auth_app.views_login_auth import login_bp
from rest_app.person_resource import rest_bp
from rest_app.classful_views import ClassBaseViews
from file_app import file_bp


def create_app(config_name: str = 'dev'):
    app = Flask(__name__)
    config_obj = config.get(config_name)
    app.config.from_object(config_obj)
    app.register_blueprint(blueprint=auth_bp)
    app.register_blueprint(blueprint=login_bp)
    app.register_blueprint(blueprint=rest_bp)
    app.register_blueprint(blueprint=file_bp)
    db.init_app(app)
    login_manager.init_app(app)
    ClassBaseViews.register(app)
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
    app.run(host='localhost', port=8100)
    # app.run(host='10.8.6.203', port=8200)
