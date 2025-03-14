"""
练习 SQL Alchemy 的 ORM，以 1.4 版本为例
2.0版本主要是 Declarative Mapping 的方式有变化。
"""
from urllib import parse
from sqlalchemy import create_engine, inspect
from sqlalchemy import MetaData, Table, Column, Integer, String, ForeignKey
from sqlalchemy.sql.expression import text, select, func
from sqlalchemy.orm import sessionmaker, Session, declarative_base, registry
# 2.0 版本引入了下面两个类，用于支持 Declarative 风格下的类型提示
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
# 注意，2.0 版本里 1.4 的 Declarative 方式仍然是可以使用的

# --------------- 连接数据库 ---------------
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
# database url的格式：dialect+driver://username:password@host:port/database
db_url = 'mysql+pymysql://{user}:{passwd}@{host}:{port}/{database}'.format(**mysql_conf)
engine = create_engine(db_url, echo=True)

# ORM 的使用从 Session 出发
session_factory: sessionmaker[Session] = sessionmaker(bind=engine)
session: Session = session_factory()

# ------- 建立 业务表映射 ----------
def P1_Mapping():
    pass
# ORM中建立表和业务对象类的映射时，有两种方式：
# 1. Declarative Mapping：新版风格
# 2. Classical Mappings：旧版风格，从1.4版本开始，又被称为 Imperative Mappings
# 两者的主要区别在于：Declarative Mapping 同时 定义表的元数据和业务对象，而 Classical Mappings 是分别定义表元数据和业务对象，然后手动映射
# 两种方式创建的映射都是一样的

# ------- 申明式定义(Declarative Mapping) ---------
def P1_1_Declarative():
    pass
# 通过 declarative_base() 函数创建 Base 类, Base 类本质上是 一个 registry 对象，它作为所有 model 类的父类，将在子类中把声明式映射过程作用于其子类
# 这个 Base 类整个程序中通常只有一个
Base = declarative_base()

# 继承 Base 类，构建映射关系
# 映射表的类被创建的时候，Base类会将定义中的所有Column对象——也就是具体字段，改写为描述符
class UserV1(Base):
    # 类属性 __tablename__ 定义了表名称
    __tablename__ = 'orm_user_v1'

    # 表的参数
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'comment': 'ORM User-V1',
        # 下面的这个属性是为了让 User 可以修改，重复定义，否则修改字段后，重新生成此类时，Base 类不允许重新注册已存在的类
        'extend_existing': True
    }

    # 定义表的各个字段
    uid = Column(Integer, primary_key=True, autoincrement=True)  # 主键
    name = Column(String(64), nullable=False)
    gender = Column(String(64), nullable=True)
    age = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<User(name={self.name}, gender={self.gender}, age={self.age}')>"

# 2.x 风格的定义如下：
class UserV11(DeclarativeBase):  # 直接继承基类 DeclarativeBase
    __tablename__ = 'orm_user_v11'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'comment': 'ORM User-V11',
        # 下面的这个属性是为了让 User 可以修改，重复定义，否则修改字段后，重新生成此类时，Base 类不允许重新注册已存在的类
        'extend_existing': True
    }
    # 定义表的各个字段，使用 Mapped[] 增加类型提示，具体字段配置使用 mapped_column，而不是使用 Column 了
    uid: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(type_=String(64), nullable=False)
    gender: Mapped[str] = mapped_column(type_=String(64), nullable=True)
    age: Mapped[int] = mapped_column(type_=Integer, nullable=True)

    def __repr__(self):
        return f"<User(name={self.name}, gender={self.gender}, age={self.age}')>"


# 上述定义的映射类，会生成一个 __table__ 属性，存放的是 Table 对象，记录了该表的元数据
print(UserV1.__table__)
print(UserV1.__table__.__class__)
# <class 'sqlalchemy.sql.schema.Table'>
# 上述的 Table 对象，又属于 MetaData 这个集合的一部分，它可以通过 Base 类的.metadata 属性访问
print(UserV1.metadata)
print(Base.metadata)
# 结果为：MetaData()
print(UserV1.metadata is Base.metadata)

# MetaData 对象实际上是一个 registry，它保存了所有已注册的表的元数据信息，同时也提供了一些用来操作表的API
# .bind 属性：底层绑定的 Engine 或者 Connection 对象
print(Base.metadata.bind)
# .tables 属性：输出当前已注册的所有表对象
print(Base.metadata.tables)
# .clear() 方法：清除 MetaData 中所有注册的表，注意，这个操作不会影响数据库
Base.metadata.clear()
# .remove(table) 方法：清除MetaData指定的表
# 上面的 UserV1 类如果没有 __table_args__ = {'extend_existing': True} 的话，就只能生成并注册一次，除非使用上面的 clear() 方法清除
# Base.metadata.remove(UserV1.__table__)

# .create_all() 方法：在数据库中创建 MetaData中注册的所有表，它有一个 tables= 参数(list of Table 对象)，可以指定创建的表，
# 默认下，只会创建不存在的表，
# Base.metadata.create_all(engine)
Base.metadata.create_all(bind=engine, tables=[UserV1.__table__])

# .drop_all() 方法：清除数据库中所有已创建的表对象，也可以接受一个 tables 参数
# Base.metadata.drop_all(bind=engine)
# Base.metadata.drop_all(bind=engine, tables=[UserV1.__table__])

# .reflect() 方法：从数据库中加载所有的表定义 ---- KEY
Base.metadata.reflect(bind=engine)
db_tables = Base.metadata.tables


# ------- 传统定义(Classical Mapping) ---------
def P1_2_Classical():
    pass
# 创建 MetaData 对象
# 1.3 版本是手动创建
# metadata_obj = MetaData()
# 1.4 版本改为使用 registry
mapper_registry = registry()
metadata_obj = mapper_registry.metadata
# 或者使用上面的 Base 对象的 metadata 属性获取已有的 MetaData
# metadata_obj = Base.metadata

# 首先按照 Core 中的方式单独定义表的元数据（Table对象）
user_v2_table = Table(
    "orm_user_v2",
    metadata_obj,
    Column("uid", Integer, primary_key=True, autoincrement=True),
    Column("name", String(64), nullable=False),
    Column("gender", String(64), nullable=True),
    Column("age", Integer, nullable=True),
    comment="ORM User-V2",
    extend_existing=True,
    mysql_engine="InnoDB"
)
# 再定义一个表示表中每一行数据的业务对象（类似于Java的bean）
class UserV2:
    # 这个类可以啥也不写
    pass

# 手动将表的元数据和业务对象映射起来
user_v2_mapper = mapper_registry.map_imperatively(UserV2, user_v2_table)
print(type(user_v2_mapper))
# <class 'sqlalchemy.orm.mapper.Mapper'>
# 创建表
user_v2_table.create(bind=engine)
print(metadata_obj.tables)


# --------------  SQL CRUD 操作  --------------
# 使用 SQL Expression Language 1.x API 进行增删查改操作
def P2_CRUD():
    pass

# 1.x 版本 和 2.x 版本中，ORM 插入记录的语法没有什么区别
def P2_1_Add():
    # Declarative 风格
    # 创建一个 UserV1 类的对象，对应于表中的一行记录
    u1 = UserV1(name='wendy', gender='female', age=18)
    print(u1.name)
    print(u1.gender)
    # 插入数据库
    session.add(u1)
    session.add_all([
        UserV1(name='jane', gender='female', age=22),
        UserV1(name='daniel', gender='male', age=28),
        UserV1(name='Rose', gender='female', age=20)
    ])
    # 提交变更
    session.commit()

    # Classical 风格下，直接使用 UserV2 类就行了，虽然在定义的时候，这个类我们啥也没写——KEY
    # 不过需要注意的是，UserV2对应的是另一个表
    u2 = UserV2(name='wendy', gender='female', age=18)
    print(u2.name)
    print(u2.gender)
    print(u2.age)
    session.add(u2)
    session.add_all([
        UserV2(name='jane', gender='female', age=22),
        UserV2(name='daniel', gender='male', age=28),
        UserV2(name='Rose', gender='female', age=20)
    ])
    session.commit()


# ORM 在1.x 和 2.x 版本最主要的区别，就是查询语法的变化
def P2_2_Query_V1():
    """
    1.x 中，ORM查询主要是使用 session.query() 创建的 Query 对象，它有如下常用的方法：
    .all(), .one(), first() 等返回指定数量结果
    .order_by(), .limit(), .offset()
    .count(), .distinct(), .group_by(),
    .filter(), .filter_by(), .where(), .having()
    .join(), .outerjoin()
    .union(), .union_all()
    .statement：返回Query对应的SQL语句形式
    .subguery()：返回当前Query对象对于的SQL语句，但是依旧封装为Query对象，通常用于子查询
    """
    # 构建查询
    q1 = session.query(UserV1).order_by(UserV1.age.desc())
    # print(type(q1))
    # <class 'sqlalchemy.orm.query.Query'>
    # 直接print，打印的是底层的SQL
    print(q1)
    # 等价于
    print(q1.statement)
    # all() 方法才触发查询
    for row in q1.all():
        print(row)
    # 返回的 row 是一个 UserV1 对象，而不是 Core 中的 Row 对象，这就是ORM的作用
    print(type(row))
    # <class '__main__.UserV1'>
    print(row.name)
    print(row.gender)
    print(row.age)

    # 但是如果查询时只指定了部分列，那么返回值也是 Row 对象
    q2 = session.query(UserV1.name, UserV1.gender).order_by(UserV1.uid).limit(2)
    print(q2.statement.compile(compile_kwargs={"literal_binds": True}))
    for row in q2.all():
        print(row)
    print(type(row))
    # <class 'sqlalchemy.engine.row.Row'>

    # where 查询
    q3 = session.query(UserV1).where(UserV1.age >= 20)
    print(q3)  # 这样打印的SQL里，查询参数只是一个占位符
    # 打印实际执行语句
    print(q3.statement.compile(compile_kwargs={"literal_binds": True}))
    # 注意，对于 delete 的操作，上面的这种打印方式就不行了
    for row in q3.all():
        print(row)
    print(type(row))
    # <class '__main__.UserV1'>

    # 聚合查询
    q4 = session.query(UserV1.gender, func.sum(UserV1.age).label('age_sum'),
                       func.count(UserV1.name).label('cnt'),
                       func.count(UserV1.gender.distinct()).label('gender_distinct'))\
        .group_by(UserV1.gender)
    print(q4.statement.compile(compile_kwargs={"literal_binds": True}))
    for row in q4.all():
        print(row)

    # ---------------------------------------------------
    # 对于 Classical 风格映射执行查询，也是直接使用 UserV2 类，虽然 UserV2 类看起来只是一个普通的Python类
    q5 = session.query(UserV2).order_by(UserV2.age).limit(2)
    print(q5)
    for row in q5.all():
        # 由于 UserV2 中并没有设置 __repr__ 方法，所以这里打印显示的内容看不出啥
        print(row)
    # 由于选择了所有字段，所以返回的 row 是一个 UserV2 对象，也不是 Core 中的 CursorResult
    print(type(row))
    print(row.name)
    print(row.gender)
    print(row.age)


def P2_2_Query_V2():
    """
    从 1.4 版本起，将 Core 和 ORM 的查询方式进行了整合，倾向于统一使用 CORE 风格的API进行查询操作 —— 这也是 2.x 版本的最大改动之一.
    从 1.4 版本起， select() 函数支持两种方式：
      1. 传入 Table 对象进行查询 —— Core 的方式
      2. 传入 Base 类的子类对象进行查询 —— ORM 的方式
    :return:
    """
    s1 = select(UserV1).where(UserV1.age >= 20)
    print(s1.compile(compile_kwargs={"literal_binds": True}))
    # 使用 session.execute() 执行查询
    res1 = session.execute(s1).all()
    print(type(res1))
    # <class 'list'>
    for row1 in res1:
        print(row1)
    # 返回的是 Row 对象，它类似于一个元组
    print(type(row1))
    # <class 'sqlalchemy.engine.row.Row'>
    print(row1[0])  # 这样拿到的才是 User 对象
    # <User(name=Rose, gender=female, age=20')>
    print(row1[0].name)

    # 使用 connection.execute 也可以
    with engine.connect() as conn:
        res11 = conn.execute(s1)
        print(type(res11))
        # <class 'sqlalchemy.engine.cursor.LegacyCursorResult'>
        for row11 in res11:
            print(row11)
    print(type(row11))
    # <class 'sqlalchemy.engine.row.LegacyRow'>
    # LegacyRow 是 Row 的子类，好像是为了兼容1.x版本的结果
    print(row11.name)
    print(row11.gender)

    s2 = select(UserV2).where(UserV2.age >= 20)
    print(s2.compile(compile_kwargs={"literal_binds": True}))
    res2 = session.execute(s2).all()
    for row2 in res2:
        print(row2)
    print(type(row2))
    # <class 'sqlalchemy.engine.row.Row'>
    print(row2[0])
    print(row2[0].name)

    # 这里是使用 Table 对象，所以需要使用 .c 属性来访问 age
    s3 = select(user_v2_table).where(user_v2_table.c.age >= 20)
    print(s3.compile(compile_kwargs={"literal_binds": True}))
    res3 = session.execute(s3).all()
    for row3 in res3:
        print(row3)
    print(type(row3))
    # <class 'sqlalchemy.engine.row.Row'>
    print(row3.name)

    # 其他查询
    s4 = select(UserV1.gender, func.sum(UserV1.age).label('age_sum'),
                func.count(UserV1.name).label('cnt'),
                func.count(UserV1.gender.distinct()).label('gender_distinct'))\
        .group_by(UserV1.gender)
    print(s4.compile(compile_kwargs={"literal_binds": True}))
    res4 = session.execute(s4).all()
    for row4 in res4:
        print(row4)


