from sqlalchemy import Table, Column, BigInteger, Integer, String, DateTime, ForeignKey, func
from sqlmodel import SQLModel, Field
from datetime import datetime
from database import metadata, Base

# 用户表示例
class AuthUser(Base):
    __tablename__ = "users"
    __table_args__ = {
        "extend_existing": True,
        'mysql_engine': 'InnoDB',
        'comment': '用户表'
    }
    uid = Column(BigInteger, autoincrement=True, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False, comment="用户名")
    phone = Column(String, unique=True, index=True, nullable=True, comment="手机号")
    password = Column(String, nullable=False, comment="密码哈希值")
    # 注意下面两个字段的默认值，是设置在服务端的
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), server_onupdate=func.now(), comment="更新时间")
