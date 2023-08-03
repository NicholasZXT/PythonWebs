from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from FlaskAuthentication.extentions import db


class User(db.Model, UserMixin):
    """
    Flask-login要求表示用户的类实现下面 4 个属性/方法：
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
        'comment': 'Flask用户表',
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

