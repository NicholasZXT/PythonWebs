"""
ORM 和 RBAC 的结合使用
"""
from urllib import parse
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, backref

mysql_conf = {
    'host': 'localhost',
    'user': 'root',
    # 'passwd': 'mysql@2018',
    # 'passwd': 'mysql2020',
    'passwd': 'mysql2022',
    'port': 3306,
    'database': 'crashcourse'
}
# 密码里的特殊字符需要做一些转义处理
mysql_conf['passwd'] = parse.quote_plus(mysql_conf['passwd'])
db_url = 'mysql+pymysql://{user}:{passwd}@{host}:{port}/{database}'.format(**mysql_conf)
engine = create_engine(db_url)

Base = declarative_base()


class User(Base):
    __tablename__ = 'rbac_user'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'comment': 'RBAC-User',
        'extend_existing': True
    }
    uid = Column(String(32), primary_key=True, comment='用户主键')
    name = Column(String(64), nullable=False, comment='用户名称')

    def __repr__(self):
        return f"<User(uid={self.uid}, name={self.name}')>"


class Group(Base):
    __tablename__ = 'rbac_group'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'comment': 'RBAC-Group',
        'extend_existing': True
    }
    gid = Column(String(32), primary_key=True, comment='组ID')
    name = Column(String(64), nullable=False, comment='组名')

    def __repr__(self):
        return f"<User(gid={self.gid}, name={self.name}')>"


class Permission(Base):
    __tablename__ = 'rbac_permission'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'comment': 'RBAC-Permission',
        'extend_existing': True
    }
    pid = Column(String(32), primary_key=True, comment='权限ID')
    name = Column(String(64), nullable=False, comment='权限名称')

    def __repr__(self):
        return f"<User(pid={self.gid}, name={self.name}')>"

