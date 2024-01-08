from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_security.datastore import SQLAlchemyUserDatastore
from flask_security.models import fsqla_v3 as fsqla
from extensions import db


class User(db.Model, UserMixin):
    """
    Flask-Login要求表示用户的类实现下面 4 个属性/方法（一般由 UserMixin 类引入）：
    1. is_authenticated
    2. is_active
    3. is_anonymous
    4. get_id(): 返回用户的 id
    方便的做法是继承 UserMixin 类，它表示通过认证的用户，所以 is_authenticated 和 is_active 属性返回 True，is_anonymous 属性返回 False,
    get_id() 方法默认会访问 User 类名为 id 的属性，如果主键属性不是 id，就需要重写一下此方法.
    """
    __tablename__ = 'flask_login_users'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'comment': 'Flask-Login用户表',
        'extend_existing': True
    }
    uid = db.Column(db.BigInteger(), comment='UID', primary_key=True, autoincrement=True)
    username = db.Column(db.String(length=64), comment='用户名')
    password_hash = db.Column(db.String(length=128), comment='密码')

    # 这里由于 User 类的主键名称不是 id，所以需要自己重写 get_id 方法
    def get_id(self):
        return self.uid

    def set_password(self, password):
        if isinstance(password, str) and len(password):
            self.password_hash = generate_password_hash(password, salt_length=4)
        else:
            raise ValueError()

    def validate_password(self, password):
        if isinstance(password, str) and len(password) and self.password_hash:
            return check_password_hash(self.password_hash, password)
        else:
            return False


# ----------------- Flask-Security的Models --------------------
"""
Flask-Security对于用户权限的管理，底层是通过下面4张表进行的：
+ User 表，记录用户信息，除了用户名和密码，还有各种各样的附加信息
+ Role 表，记录了具体的权限信息
+ UserRole 表，上面两个表的关联表
+ WebAuth 表，记录WebAuth的信息
其中表里的有些字段和方法是必须要有的，因此Flask-Security在如下两个地方作了规定：
1. core.py 中定义了 UserMixin, RoleMixin, WebAuthnMixin ，定义了上面这些表的 Model 需要实现哪些方法，并且已经帮我们实现了
2. datastore.py 中定义了 User, Role, WebAuthn，这个3个类只是**类型申明**，不是具体实现，里面描述了各个 Model类 需要有的字段
有了上面 3 个表之后，Flask-Security 还提供了一个统一管理上面 3 个类（UserRole类不需要主动管理）的封装：DataStore + UserDatastore，
位于 datastore.py 文件中，其中 DataStore用于抽象底层的具体数据库，UerDatastore 用于封装上面的3个类，实际使用中有如下几个实现：
1. SQLAlchemyUserDatastore：底层使用 Flask-SQLAlchemy 这个插件来管理表
2. SQLAlchemySessionUserDatastore：底层直接使用 SQLAlchemy 来管理表
3. PeeweeUserDatastore：底层使用 Flask-Peewee 插件来管理表
4. MongoEngineUserDatastore：底层使用 Flask-MongoEngine 插件来管理表
前面3个底层都是使用的MySQL作为引擎。
如果使用MySQL作为引擎的话，建议使用第一个的 SQLAlchemyUserDatastore，因为Flask-Security为此提供了一个models模块，
里面使用 Flask-SQLAlchemy 插件，帮我们实现了上面 3 个类的字段定义 + 对应Mixin类 的组合（没有继承 Model 类），使用起来更方便。
如果使用 2、3的话，需要我们手动参考 datastore.py 里各个类的字段，并混入各个 Mixin 类，麻烦一点。
"""
# 使用流程如下：
# 第1步：使用 FsModels 设置一下 db —— 它是 Flask-Sqlalchemy 提供的 SQLAlchemy 对象
user_table_name = 'security_user'
role_table_name = 'security_role'
fsqla.FsModels.set_db_info(appdb=db, user_table_name=user_table_name, role_table_name=role_table_name)

# 第2步：定义 User Model 和 Role Model，需要自己继承 db.Model，并混入相应的 Mixin 类，类的定义体为空就行
class SecurityUser(db.Model, fsqla.FsUserMixin):
    __tablename__ = user_table_name


class SecurityRole(db.Model, fsqla.FsRoleMixin):
    __tablename__ = role_table_name


# 第3步：使用 SQLAlchemyUserDatastore 对上面的 User 和 Role 表进行管理，并传入底层数据库引擎对象 db
# 后面这个 user_datastore 对象会交给 Security 对象，Security对象也是通过此对象来对底层的表进行 CRUD 操作
user_datastore = SQLAlchemyUserDatastore(db=db, user_model=SecurityUser, role_model=SecurityRole)
