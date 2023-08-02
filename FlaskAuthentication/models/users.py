from extentions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model, UserMixin):
    __tablename__ = 'flask_login_users'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'comment': 'Flask用户表'
    }
    uid = db.Column(db.String(length=16), comment='UID', primary_key=True)
    username = db.Column(db.String(length=64), comment='用户名')
    password_hash = db.Column(db.String(length=64), comment='密码')

    def set_password(self, password):
        if isinstance(password, str) and len(password):
            self.password_hash = generate_password_hash(password)
        else:
            raise ValueError()

    def validate_password(self, password):
        if isinstance(password, str) and len(password) and self.password_hash:
            return check_password_hash(self.password_hash, password)
        else:
            return False

