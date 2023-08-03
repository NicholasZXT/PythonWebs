from flask import Flask
from configs.flask_config import config
from extentions import db, auth, login_manager
from views import *


def create_app(config_name: str = 'dev'):
    app = Flask(__name__)
    config_obj = config.get(config_name)
    app.config.from_object(config_obj)
    app.register_blueprint(blueprint=auth_bp)
    app.register_blueprint(blueprint=login_bp)
    db.init_app(app)
    login_manager.init_app(app)
    return app


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # 必须要导入表定义才能创建
        # 但是这里要求 views.__init__.py 文件中，必须使用 import * 的方式，否则 User 表不生效，原因未知
        from FlaskAuthentication.models import User
        print("****** creating all tables... ******")
        db.create_all()
        print("****** creating all tables done. ******")
    # print(app.url_map)
    app.run(host='localhost', port=8100)
