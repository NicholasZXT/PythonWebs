"""
练习 SQL Alchemy 的 ORM 的关系定义，以 1.4 版本为例
"""
from urllib import parse
from sqlalchemy import create_engine, Table, Column, Integer, String, ForeignKey
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
mysql_conf['passwd'] = parse.quote_plus(mysql_conf['passwd'])
db_url = 'mysql+pymysql://{user}:{passwd}@{host}:{port}/{database}'.format(**mysql_conf)
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()


# ---------------------------------------------------------------------
def P1_1_v_n():
    print("一对多关系")

class Parent1vN(Base):
    __tablename__ = "parent_table_1vn"
    id = Column(Integer, primary_key=True)
    # 使用 relationship 函数，创建一个映射关系的字段
    # one-to-many collection: 复数形式 children，表示对应多个 child 记录
    children = relationship("Child1vN")
    # children = relationship("Child1vN", back_populates="parent")

class Child1vN(Base):
    __tablename__ = "child_table_1vn"
    id = Column(Integer, primary_key=True)
    # n 的表里面，使用 ForeignKey 指定父表的外键, 其中的参数是 外键表名称.外键字段
    parent_id = Column(Integer, ForeignKey("parent_table_1vn.id"))
    # many-to-one scalar: 单数形式 parent，表示只对应一个 parent 记录
    parent = relationship("Parent1vN", back_populates="children")


# ---------------------------------------------------------------------
def P2_n_v_1():
    print("多对一关系")

# 其实就是上面情况的反向定义
class ParentNv1(Base):
    __tablename__ = "parent_table_nv1"
    id = Column(Integer, primary_key=True)
    # 总之，哪个是 n 的表，就在哪个表中定义 ForeignKey
    child_id = Column(Integer, ForeignKey("child_table_nv1.id"))
    # many-to-one scalar: 单数 child，表示只对应一个 child 记录
    child = relationship("ChildNv1", back_populates="parents")

class ChildNv1(Base):
    __tablename__ = "child_table_nv1"
    id = Column(Integer, primary_key=True)
    # one-to-many collection: 复数 parents，表示多个 parent 记录
    parents = relationship("ParentNv1", back_populates="child")


# ---------------------------------------------------------------------
def P3_1_v_1():
    print("一对一关系")

# 在 1 vs n 的基础上进行修改
class Parent1v1(Base):
    __tablename__ = "parent_table_1v1"
    id = Column(Integer, primary_key=True)
    # 在 1 vs n 中，这里本来是 多条 child 记录
    # children = relationship("Child1vN", back_populates="parent")
    # 使用 userlist=False，限制只有 1 条child，如果查询时有多条 child 记录，则会报 warning
    children = relationship("Child1vN", back_populates="parent", uselist=False)

class Child1v1(Base):
    __tablename__ = "child_table_1v1"
    id = Column(Integer, primary_key=True)
    # 这里定义了 ForeignKey，因此 Child 是 n 的一方
    parent_id = Column(Integer, ForeignKey("parent_table_1v1.id"))
    # many-to-one scalar：表示 对应一个 parent 记录 —— 相比与 1 vs n 中，这里没有变化
    parent = relationship("Parent", back_populates="children")


# ---------------------------------------------------------------------
def P4_n_v_n():
    print("多对多关系")

# 多对多关系的定义，则需要引入一个专门表示关联关系的三方表
# ****** 第一种方式，采用 Core 的方式来定义关联表，此时关联表中，只有两个字段 ******
association_table_v1 = Table(
    "association_table_v1",
    Base.metadata,
    # 这个关联表中
    Column("left_id", ForeignKey("left_table_v1.id"), primary_key=True),
    Column("right_id", ForeignKey("right_table_v1.id"), primary_key=True)
)

class LeftV1(Base):
    __tablename__ = "left_table_v1"
    id = Column(Integer, primary_key=True)
    # 使用 secondary 参数指定关联表
    right_records = relationship("RightV1", secondary=association_table_v1, back_populates="left_records")

class RightV1(Base):
    __tablename__ = "right_table_v1"
    id = Column(Integer, primary_key=True)
    left_records = relationship("LeftV1", secondary=association_table_v1, back_populates="right_records")

# ****** 第二种方式，采用 ORM 的方式来定义关联表，此时关联表中，可以增加一些额外信息的字段 ******
class Association(Base):
    __tablename__ = "association_table_v2"
    left_id = Column(ForeignKey("left_table_v2.id"), primary_key=True)
    right_id = Column(ForeignKey("right_table_v2.id"), primary_key=True)
    # 其他字段信息
    extra_data = Column(String(50))
    left_records = relationship("LeftV2", back_populates="right_records")
    right_records = relationship("RightV2", back_populates="left_records")


class LeftV2(Base):
    __tablename__ = "left_table_v2"
    id = Column(Integer, primary_key=True)
    right_records = relationship("Association", back_populates="left_records")


class RightV2(Base):
    __tablename__ = "right_table_v2"
    id = Column(Integer, primary_key=True)
    left_records = relationship("Association", back_populates="right_records")