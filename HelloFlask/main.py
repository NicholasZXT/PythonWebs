import logging
from flask import Flask
from configs import config
from extensions import db
from rest_app.views_restful import restful_bp
from rest_app.views_classful import ClassBasedViews
from auth_app.exts import auth, login_manager, jwt, principal, security
from auth_app.views_rest_auth import auth_bp
from auth_app.views_login_auth import login_bp
from auth_app.views_jwt_auth import jwt_bp
from auth_app.views_principal import principal_bp
from auth_app.views_security import security_bp
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
    app.register_blueprint(blueprint=security_bp)
    # ------ 初始化扩展 ---------
    db.init_app(app)
    app.db = db  # 设置一下，以便在 flask-shell 或者 with app.app_context() 里拿到 db 对象进行调试
    ClassBasedViews.register(app)
    login_manager.init_app(app)
    jwt.init_app(app)
    principal.init_app(app)
    # Flask-security初始化
    security.init_app(app=app)
    return app


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # 必须要导入表定义才能创建
        from auth_app.models import User, SecurityUser, Role
        print("****** creating all tables... ******")
        # db.create_all()
        print("****** creating all tables done. ******")
    print(app.url_map)
    app.logger.setLevel(logging.DEBUG)
    app.run(host='localhost', port=8100)
    # app.run(host='10.8.6.203', port=8200)

    # 测试 Flask-Security 使用
    with app.app_context():
        from flask_security import SQLAlchemyUserDatastore, hash_password
        security_ext = app.extensions['security']
        # db = app.extensions['sqlalchemy']
        db = app.db
        datastore: SQLAlchemyUserDatastore = security_ext.datastore
        # 创建角色时，只需要以关键字参数形式传入 Role 表里字段和对应的值即可，其中 permissions 字段是一个字符串，以逗号分隔多个权限
        role_admin = {'name': 'admin', 'description': 'administrator', 'permissions': 'admin,add,read,update,delete'}
        role_add = {'name': 'add', 'description': 'add something', 'permissions': 'add'}
        role_update = {'name': 'update', 'description': 'update something', 'permissions': 'update'}
        # 创建用户也一样，以关键字参数传入 User 表对应字段和值，其中 email 字段是必须的，作为用户身份标识，用户名非必须，密码明文需要做hash处理
        # 用户表的唯一标识 fs_uniquifier 会自动生成，当然也可以自己提供，覆盖自动生成的值
        # roles 需要是list of str|Role，创建时会对 role 进行检查，不存在的 role 会被置为 None，导致用户创建不成功
        user_admin = {'email': 'admin@flask.com', 'username': 'admin_user', 'password': hash_password('pw-admin'),
                      'roles': ['admin', 'add', 'update']}
        user_ming = {'email': 'ming@flask.com', 'username': 'ming', 'password': hash_password('pw-ming'),
                     'roles': ['add', 'update']}
        user_hong = {'email': 'hong@flask.com', 'username': 'hong', 'password': hash_password('pw-hong'),
                     'roles': ['add']}
        # 创建角色
        role_admin_rec = datastore.create_role(**role_admin)
        role_add_rec = datastore.create_role(**role_add)
        role_update_rec = datastore.create_role(**role_update)
        # 创建用户
        user_admin_rec = datastore.create_user(**user_admin)
        user_ming_rec = datastore.create_user(**user_ming)
        user_hong_rec = datastore.create_user(**user_hong)
        # 通过角色名查询角色
        role_res = datastore.find_role(role='admin')
        role_res = datastore.find_or_create_role(name='admin2', description='admin role 2', permissions='admin,add,read')
        # 查询用户，关键字参数传入查询字段和条件
        user_res = datastore.find_user(email='admin@flask.com')
        user_res = datastore.find_user(username='ming')
        # 获取用户的角色，但无法直接获取角色的权限
        print(user_res.roles)
        # 只能遍历获取
        for role in user_res.roles:
            # 注意，permissions 返回的是一个 list of str
            print(role.permissions)
        # 给角色添加权限
        datastore.add_permissions_to_role(role='add', permissions='delete,update')
        # 给用户添加角色，用户必须是 User 对象, 一次只能添加一个 role，返回值 True/False 表示是否添加成功
        datastore.add_role_to_user(user=user_res, role='update')

        # 上面除了查询之外的操作，都需要提交事务，或者回滚
        db.session.commit()
        # db.session.rollback()
