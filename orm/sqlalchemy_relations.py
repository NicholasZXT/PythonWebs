"""
练习 SQL Alchemy 的 ORM 的关系定义，以 1.4 版本为例
"""
from urllib import parse
from sqlalchemy import create_engine, Table, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, backref
from sqlalchemy.sql.expression import text, select, func
from sqlalchemy.ext.associationproxy import association_proxy

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
# session.close()

Base = declarative_base()


# ---------------------------------------------------------------------
def P1_1_v_n():
    print("一对多关系")

class Parent1vN(Base):
    __tablename__ = "parent_table_1vn"
    __table_args__ = {'mysql_engine': 'InnoDB', 'extend_existing': True}
    id = Column(Integer, primary_key=True)
    # 使用 relationship 函数，创建一个映射关系的字段
    # one-to-many collection: 复数形式 children，表示对应多个 child 记录
    # children = relationship("Child1vN")
    children = relationship("Child1vN", back_populates="parent")

    def __repr__(self):
        return f"<Parent1vN(id={self.id})>"

class Child1vN(Base):
    __tablename__ = "child_table_1vn"
    __table_args__ = {'mysql_engine': 'InnoDB', 'extend_existing': True}
    id = Column(Integer, primary_key=True)
    # n 的表里面，使用 ForeignKey 指定父表的外键, 其中的参数是 外键表名称.外键字段
    parent_id = Column(Integer, ForeignKey("parent_table_1vn.id"))
    # many-to-one scalar: 单数形式 parent，表示只对应一个 parent 记录
    parent = relationship("Parent1vN", back_populates="children")

    def __repr__(self):
        return f"<Child1vN(id={self.id}, parent_id={self.parent_id})>"

def run_1():
    Base.metadata.create_all(bind=engine, tables=[Parent1vN.__table__, Child1vN.__table__])
    # 生成数据
    p1 = Parent1vN(id=1)
    p2 = Parent1vN(id=2)
    c1 = Child1vN(id=1, parent_id=1)
    c2 = Child1vN(id=2, parent_id=1)
    c3 = Child1vN(id=3, parent_id=2)
    c4 = Child1vN(id=4, parent_id=2)
    session.add_all(instances=[p1, p2, c1, c2, c3, c4])
    session.commit()
    # 查询
    s1 = select(Parent1vN).where(Parent1vN.id == 1)
    print(s1.compile(compile_kwargs={"literal_binds": True}))
    r1 = session.execute(s1).all()
    r1_p1 = r1[0][0]
    # print(p1 == r1_p1)
    print(r1_p1)
    # 通过 children 属性，可以直接拿到 p1 记录对应的多个 child 记录（list of Child1vN）
    r1_p1_children = r1_p1.children
    print(r1_p1_children)

    s2 = select(Child1vN).where(Child1vN.id == 3)
    print(s2.compile(compile_kwargs={"literal_binds": True}))
    r2 = session.execute(s2).all()
    r2_c3 = r2[0][0]
    print(r2_c3)
    # 通过 parent 属性直接拿到 对应的 单条 parent 记录
    print(r2_c3.parent)

# ---------------------------------------------------------------------
def P2_n_v_1():
    print("多对一关系")

# 其实就是上面情况的反向定义
class ParentNv1(Base):
    __tablename__ = "parent_table_nv1"
    __table_args__ = {'mysql_engine': 'InnoDB', 'extend_existing': True}
    id = Column(Integer, primary_key=True)
    # 总之，哪个是 n 的表，就在哪个表中定义 ForeignKey
    child_id = Column(Integer, ForeignKey("child_table_nv1.id"))
    # many-to-one scalar: 单数 child，表示只对应一个 child 记录
    child = relationship("ChildNv1", back_populates="parents")

    def __repr__(self):
        return f"<ParentNv1(id={self.id}, child_id={self.child_id})>"

class ChildNv1(Base):
    __tablename__ = "child_table_nv1"
    __table_args__ = {'mysql_engine': 'InnoDB', 'extend_existing': True}
    id = Column(Integer, primary_key=True)
    # one-to-many collection: 复数 parents，表示多个 parent 记录
    parents = relationship("ParentNv1", back_populates="child")

    def __repr__(self):
        return f"<ChildNv1(id={self.id})>"


# ---------------------------------------------------------------------
def P3_1_v_1():
    print("一对一关系")

# 在 1 vs n 的基础上进行修改
class Parent1v1(Base):
    __tablename__ = "parent_table_1v1"
    __table_args__ = {'mysql_engine': 'InnoDB', 'extend_existing': True}
    id = Column(Integer, primary_key=True)
    # 在 1 vs n 中，这里本来是 多条 child 记录
    # children = relationship("Child1vN", back_populates="parent")
    # 使用 userlist=False，限制只有 1 条child，如果查询时有多条 child 记录，则会报 warning
    children = relationship("Child1vN", back_populates="parent", uselist=False)

    def __repr__(self):
        return f"<Parent1v1(id={self.id})>"

class Child1v1(Base):
    __tablename__ = "child_table_1v1"
    __table_args__ = {'mysql_engine': 'InnoDB', 'extend_existing': True}
    id = Column(Integer, primary_key=True)
    # 这里定义了 ForeignKey，因此 Child 是 n 的一方
    parent_id = Column(Integer, ForeignKey("parent_table_1v1.id"))
    # many-to-one scalar：表示 对应一个 parent 记录 —— 相比与 1 vs n 中，这里没有变化
    parent = relationship("Parent", back_populates="children")

    def __repr__(self):
        return f"<Child1v1(id={self.id}, parent_id={self.parent_id})>"


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
    __table_args__ = {'mysql_engine': 'InnoDB', 'extend_existing': True}
    id = Column(Integer, primary_key=True)
    # 使用 secondary 参数指定关联表
    right_records = relationship("RightV1", secondary=association_table_v1, back_populates="left_records")

    def __repr__(self):
        return f"<LeftV1(id={self.id})>"

class RightV1(Base):
    __tablename__ = "right_table_v1"
    __table_args__ = {'mysql_engine': 'InnoDB', 'extend_existing': True}
    id = Column(Integer, primary_key=True)
    left_records = relationship("LeftV1", secondary=association_table_v1, back_populates="right_records")

    def __repr__(self):
        return f"<RightV1(id={self.id})>"

# ****** 第二种方式，采用 ORM 的方式来定义关联表，此时关联表中，可以增加一些额外信息的字段 ******
class LeftV2(Base):
    __tablename__ = "left_table_v2"
    __table_args__ = {'mysql_engine': 'InnoDB', 'extend_existing': True}
    id = Column(Integer, primary_key=True)
    # 复数形式，但是要注意，back_populates 参数中关联的 Association.left_record 字段是单数的，原因见下面
    right_associations = relationship("Association", back_populates="left_record")
    # 上面的关联，拿到的是 Association 表的记录，并不是直接拿到的 RightV2 的记录，还需要下面的关联代理来简化访问
    # 第一个参数 target_collection 指定上面的 Association 记录集合，第2个参数指定要访问的属性
    right_records = association_proxy('right_associations', 'id')

    # 为了配合关联代理使用，还需要创建一个构造方法
    def __init__(self, id):
        self.id = id

    def __repr__(self):
        return f"<LeftV2(id={self.id})>"

class RightV2(Base):
    __tablename__ = "right_table_v2"
    __table_args__ = {'mysql_engine': 'InnoDB', 'extend_existing': True}
    id = Column(Integer, primary_key=True)
    # 复数形式
    left_associations = relationship("Association", back_populates="right_record")
    # 关联代理
    left_records = association_proxy('left_associations', 'id')

    def __init__(self, id):
        self.id = id

    def __repr__(self):
        return f"<RightV2(id={self.id})>"

class Association(Base):
    __tablename__ = "association_table_v2"
    __table_args__ = {'mysql_engine': 'InnoDB', 'extend_existing': True}
    left_id = Column(ForeignKey("left_table_v2.id"), primary_key=True)
    right_id = Column(ForeignKey("right_table_v2.id"), primary_key=True)
    # 其他字段信息
    extra_data = Column(String(50))
    # 关联字段，注意，是单数形式，因为 Association 作为中间表，它和 LeftV2（或RightV2）之间是一对多的关系，
    # 并且它本身是 n 的这一方，每条记录只能对应一个 LeftV1 或者 RightV2 记录
    # 注意，back_populates 指定的 LeftV2/RightV2 中的字段都是复数形式的
    left_record = relationship("LeftV2", back_populates="right_associations")
    right_record = relationship("RightV2", back_populates="left_associations")

    def __repr__(self):
        return f"<Association(left_id={self.left_id}, right_id={self.right_id}, extra_data={self.extra_data})>"


def run_2():
    Base.metadata.create_all(bind=engine, tables=[LeftV2.__table__, RightV2.__table__, Association.__table__])
    # 生成数据
    l1 = LeftV2(id=1)
    l2 = LeftV2(id=2)
    r1 = RightV2(id=1)
    r2 = RightV2(id=2)
    a1 = Association(left_id=1, right_id=1, extra_data='a1')
    a2 = Association(left_id=1, right_id=2, extra_data='a2')
    a3 = Association(left_id=2, right_id=1, extra_data='a3')
    a4 = Association(left_id=2, right_id=2, extra_data='a4')
    session.add_all(instances=[l1, l2, r1, r2, a1, a2, a3, a4])
    session.commit()

    # 查询
    s1 = select(LeftV2).where(LeftV2.id == 1)
    print(s1.compile(compile_kwargs={"literal_binds": True}))
    r1 = session.execute(s1).all()
    r1_l1 = r1[0][0]
    # 拿到的是 Association 的多条记录列表，
    print(r1_l1.right_associations)
    # 如果要进一步拿到对应的 多条 RightV2 记录，还需要进行遍历关联访问
    for association in r1_l1.right_associations:
        print(association.right_record)
    # 使用关联代理来直接访问 RightV2 记录里的某个属性列表
    print(r1_l1.right_records)
