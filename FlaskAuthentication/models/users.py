from extentions import db


class User(db.Model):
    __tablename__ = 'flask_users'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'comment': '用户表'
    }
    uid = db.Column(db.String(length=16), comment='UID', primary_key=True)
    user_name = db.Column(db.String(length=64), comment='用户名')
    password_hash = db.Column(db.String(length=64), comment='密码')

