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
+ WebAuth 表，记录WebAuth的信息
+ UserRole 表，用于管理 User 和 Role 之间多对多关系的关联表，一般不需要开发者手动管理
其中表里的有些字段和方法是必须要有的，因此Flask-Security在如下两个地方提供了模板：
1. core.py 中定义了 UserMixin, RoleMixin, WebAuthnMixin ，定义并实现了上面这些表的 Model 需要提供的一些方法.
   其中 UserMixin 是继承的 Flask-Login 的 UserMixin 类
2. datastore.py 中进一步定义了上面3个mixin类的子类：User(UserMixin), Role(RoleMixin), WebAuthn(WebAuthnMixin)，
   不过这3个子类都只是定义了各个 Model类 的字段，没有定义方法，只是作为**类型申明**，在datastore.py中用于类型提示
有了上面 3 个表之后，Flask-Security 还提供了一个统一管理上面 3 个类（UserRole类不需要主动管理）的封装：DataStore + UserDatastore，
位于 datastore.py 文件中，其中 DataStore用于抽象底层的具体数据库，UerDatastore 用于封装上面的3个类，提供一些对 User/Role 进行 CRUD 的方法.

从上面可以看出，Flask-Security 实现的RBAC粒度比较粗，权限只到Role这一层，因为它并没有提供一个 Permission 表来存储具体的权限，
不像 Django 那样提供了 Permission表（还有对应的role_permission关联表），因此不能实现 Object级别（也就是记录级别）的权限控制。

UerDatastore 有如下几个实现：
1. SQLAlchemyUserDatastore：底层使用 Flask-SQLAlchemy 这个插件来管理表
2. SQLAlchemySessionUserDatastore：用户直接提供 SQLAlchemy 的 session，不过内部还是使用上面的 SQLAlchemyUserDatastore 来管理表
3. PeeweeUserDatastore：底层使用 Flask-Peewee 插件来管理表
4. MongoEngineUserDatastore：底层使用 Flask-MongoEngine 插件来管理表
前面3个底层都是使用的MySQL作为引擎。
如果使用MySQL作为引擎的话，建议使用第一个的 SQLAlchemyUserDatastore，因为Flask-Security为此提供了一个models模块，
里面使用 Flask-SQLAlchemy 插件，帮我们实现了上面 3 个类的字段定义 + 对应Mixin类 的组合，使用起来方便一些，
不过这3个类并没有继承 SQLAlchemy.Model 类，需要手动设置一下，下面会展示；
如果使用 2、3的话，需要我们手动参考 datastore.py 里 User, Role, WebAuthn 提示的字段手动定义，并混入各个 Mixin 类，麻烦一点。
"""
# 使用流程如下：
# 第1步：使用 FsModels 设置一下 db —— 它是 Flask-Sqlalchemy 提供的 SQLAlchemy 对象
user_table_name = 'security_user'
role_table_name = 'security_role'
# 最后会生成 security_user, security_role, roles_users 这3个表
# db 是 Flask-SQLAlchemy 插件的 SQLAlchemy 对象，这里因为自定义了 user_table 和 role_table 的名称，所以也要设置一下
fsqla.FsModels.set_db_info(appdb=db, user_table_name=user_table_name, role_table_name=role_table_name)

# 第2步：定义 User Model 和 Role Model，需要自己继承 db.Model，并混入相应的 Mixin 类，类的定义体为空即可。
# 原因就在于 FsUserMixin 这些类中只定义了字段和操作，但是并没有引入 SQLAlchemy.Model，
# 所以需要开发者专门定义一个类，来继承 db.Model，并混入相应的 Mixin 类
# 这里由于自定义了 表名称，所以也需要设置一下，此外，还可以自定义表的各种全局属性（通过 __table_args__）
class SecurityUser(db.Model, fsqla.FsUserMixin):
    __tablename__ = user_table_name


class SecurityRole(db.Model, fsqla.FsRoleMixin):
    __tablename__ = role_table_name

# 第3步：使用 SQLAlchemyUserDatastore 对上面的 User 和 Role 表进行管理，并传入Flask-SQLAlchemy的SQLAlchemy对象（通常叫 db）
# 后面这个 user_datastore 对象会交给 Security 对象，Security对象也是通过此对象来对数据库里的 User, Role表进行 CRUD 操作
user_datastore = SQLAlchemyUserDatastore(db=db, user_model=SecurityUser, role_model=SecurityRole)
# 如果是使用 SQLAlchemySessionUserDatastore，则需要 自己定义实现 User, Role 类的各个字段，并混入 core.py 中的 UserMixin，RoleMixin
# 然后以下面的方式创建，而且第一个参数是 SQLAlchemy 的 session 对象，总之相对比较麻烦
# user_datastore = SQLAlchemySessionUserDatastore(db_session, User, Role)
