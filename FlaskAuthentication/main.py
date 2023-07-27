import logging
from flask import Flask
from configs.flask_config import config
from extentions import db, auth
from views import *


def create_app(config_name: str = 'dev'):
    app = Flask(__name__)
    config_obj = config.get(config_name)
    app.config.from_object(config_obj)
    app.register_blueprint(blueprint=bp1)
    db.init_app(app)
    return app


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # 必须要导入表定义才能创建
        from models.users import User
        print("****** creating all tables... ******")
        # db.create_all()
        print("****** creating all tables done. ******")
    # print(app.url_map)
    app.run(host='localhost', port=8100)
