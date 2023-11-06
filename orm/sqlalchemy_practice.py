"""
以下示例，均是 1.4 版本的 SQLAlchemy

以下的查询表均来自《MySQL必知必会》附带的数据表，下载地址为:https://forta.com/books/0672327120/
"""
from urllib import parse
from sqlalchemy import create_engine
from sqlalchemy.sql.expression import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData, Table, Column, Integer, String, ForeignKey
from sqlalchemy.sql import select, func
from sqlalchemy.dialects import mysql

# --------------- 1. 连接数据库 ---------------
def P1_Engine():
    pass

mysql_conf = {
    'host': 'localhost',
    'user': 'root',
    # 'passwd': 'mysql@2018',
    'passwd': 'mysql2022',
    'port': 3306,
    'database': 'crashcourse'
}
# 密码里的特殊字符需要做一些转义处理
mysql_conf['passwd'] = parse.quote_plus(mysql_conf['passwd'])
# database url的格式：dialect+driver://username:password@host:port/database
# 其中的 driver 是底层的数据库驱动，注意，SQLAlchemy 本身是 不提供 数据库驱动的，需要安装对应的驱动依赖
db_url = 'mysql+pymysql://{user}:{passwd}@{host}:{port}/{database}'.format(**mysql_conf)
# 创建数据库的连接对象Engine，注意，此时并未执行连接操作
# Engine 包括数据库连接池 （Pool) 和 方言 (Dialect，指不同数据库 sql 语句等的语法差异)，两者一起以符合 DBAPI 规范的方式与数据库交互
# engine = create_engine(db_url)
# 设置 echo=True 的话，每一步则会打印出底层实际执行的SQL
engine = create_engine(db_url, echo=True)

# 获取数据库里的表名称
# tables = engine.table_names()
# print(tables)
# ['customers', 'orderitems', 'orders', 'productnotes', 'products', 'vendors']

# 有了`Engine`对象之后，可以通过如下两种方式执行对数据库的操作（[Working with Engines and Connections](https://docs.sqlalchemy.org/en/14/core/connections.html)）：
# 1. `Connection`对象：这个就是类似于 PEP-249 规范里定义的使用方式，通过`Connection`对象创建`Cursor`对象，执行SQL语句
# 2. `Session`对象：这个通常和SQLAlchemy-ORM配合使用

# ------------ 1.1 使用 Connection -------------------
def P1_1_Connection():
    pass

# （1）创建连接对象
with engine.connect() as connection:
    # .connect 返回的是 Connection 对象，在上面执行 execute 方法，传入原生的 SQL 语句
    # result = connection.execute("select * from customers")
    # 不过推荐的做法是，使用 text 函数来封装一下 SQL 语句
    result = connection.execute(text("select * from customers"))
    # execute() 返回的是 CursorResult 对象，可以通过迭代的方式读取其中的数据
    for row in result:
        print("row:", row)
print(row.__class__)
# sqlalchemy.engine.row.LegacyRow
print(row.items())
# [('cust_id', 10005), ('cust_name', 'E Fudd'), ('cust_address', '4545 53rd Street'), ('cust_city', 'Chicago')]
print(row.values())
# [10005, 'E Fudd', '4545 53rd Street', 'Chicago', 'IL', '54545', 'USA', 'E Fudd', None]
# 可以通过如下3种方式访问属性
print(row[0])
print(row.cust_id)
print(row['cust_id'])

# （2）使用游标
# 游标对象不是SQLAlchemy提供的，而是由底层的数据库驱动提供的，所以要获取游标对象，需要先获取底层驱动原生的数据库连接对象
connection = engine.raw_connection()
try:
    cursor_obj = connection.cursor()
    res_num = cursor_obj.execute("select * from customers")
    print(f"res_num: {res_num}")
    results = list(cursor_obj.fetchall())
    print("results:")
    print(results)
    cursor_obj.close()
    connection.commit()
finally:
    connection.close()
# 此外，也可以通过 SQLAlchemy 的 Connection 对象的 .connection 属性获取底层的驱动的 Connection 对象，不过这个方式好像有些限制
try:
    con = engine.connect()
    print(con.__class__)
    # <class 'sqlalchemy.engine.base.Connection'>
    connection = con.connection
    print(connection.__class__)
    # <class 'sqlalchemy.pool.base._ConnectionFairy'>
    cursor_obj = connection.cursor()
    res_num = cursor_obj.execute("select * from customers")
    print(f"res_num: {res_num}")
    results = list(cursor_obj.fetchall())
    print("results:")
    print(results)
    cursor_obj.close()
    connection.commit()
finally:
    connection.close()
    con.close()


# （3） 使用事务
# Connection.begin() 方法会返回一个事务对象 Transaction，该对象有 .close(), .commit(), .rollback() 方法，
# 但是没有.begin()方法，因为 Connection.begin() 的时候就已经表示事务的开启了
# 事务通常和上下文管理一起使用
with engine.connect() as connection:
    with connection.begin():
        connection.execute(text("select * from customers"))
# 一个简便的写法是：
with engine.begin() as connection:
    connection.execute(text("select * from customers"))


#  -------------- 1.2 使用 Session --------------
def P1_2_Session():
    pass
# 使用 SQLAlchemy-ORM 和数据库沟通时，不会直接使用上面的 engine，而是引入一个 Session 类，它通常由 sessionmaker() 这个工厂方法返回
# 所有 ORM 对象的载入和保存都需要通过session对象进行，有两种方式创建 Session 对象
# 第一种，创建时直接配置engine
# Session = sessionmaker(bind=engine)
# 第2种，先创建，后配置 engine
# Session = sessionmaker()
# Session.configure(bind=engine)

# 上述的 sessionmaker() 是一个工厂方法，它返回的 Session 是一个类，实例化这个类会得到一个绑定 Engine 对象的 Session 对象
# session = Session()

# session的常见操作方法包括
# .begin() :开启事务，可以配合 with 使用
# .flush()：预提交，提交到数据库文件，还未写入数据库文件中
# .commit()：提交了一个事务
# .rollback()：回滚
# .close()：关闭事务

# .connection()：返回一个 Connection 对象
# .execute(): 执行原生SQL查询

# 与 ORM 相关的操作有：
# .add()
# .add_all()
# .query(): 执行查询，返回一个 Query 对象，这个是最重要的查询入口


# --------------- 2. 建立映射 ---------------
def P2_Mapping():
    pass
# 建立类和数据库表的映射关系，有两种定义映射的方式：
# 1. Declarative Mapping：这个是新版的风格，即 ORM 风格 —— 推荐这个
# 2. Classical Mappings：这个是旧版的风格，更加底层，使用方式类似于原生SQL，从1.4版本开始，这个又被称为 Imperative Mappings

# 2.1 ------- 申明式定义(Declarative Mapping) ---------
def P2_1_Declarative():
    pass
# 通过 declarative_base() 函数创建 Base 类, Base 类本质上是 一个 registry 对象，它作为所有 model 类的父类，将在子类中把声明式映射过程作用于其子类
# 这个 Base 类整个程序中通常只有一个
Base = declarative_base()

# 继承 Base 类，构建映射关系
# 映射表的类被创建的时候，Base类会将定义中的所有Columne对象——也就是具体字段，改写为描述符
class UserV1(Base):
    # 类属性 __tablename__ 定义了表名称
    __tablename__ = 'user_v1'

    # 表的参数
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'comment': 'User table',
        # 下面的这个属性是为了让 User 可以修改，重复定义，否则修改字段后，重新生成此类时，Base 类不允许重新注册已存在的类
        'extend_existing': True
    }

    # 定义表的各个字段
    id = Column(Integer, primary_key=True)  # 主键
    name = Column(String(64))
    gender = Column(String(64))
    age = Column(Integer)
    province = Column(String(64))

    def __repr__(self):
        return f"<User(name={self.name}, gender={self.gender}, age={self.age}, province='{self.province}')>"


# 上述定义的映射类，会生成一个 __table__ 属性，存放的是 Table 对象，记录了该表的元数据，也就是 类与表的映射关系
print(UserV1.__table__)
print(UserV1.__table__.__class__)

# Table 对象是 Classical Mapping 里定义映射的底层实现 ---- KEY
# 上述的 Table 对象，又属于 MetaData 这个集合的一部分，它可以通过 Base 类的.metadata 属性访问
print(UserV1.metadata)
print(Base.metadata)
# 结果为：MetaData()

# MetaData 对象实际上是一个 registry，它保存了已注册的表对应的ORM对象，同时也提供了一些用来操作表的API
# .bind 属性：底层绑定的 Engine 或者 Connection 对象
print(Base.metadata.bind)

# .tables 属性：输出当前已注册的所有表对象
print(Base.metadata.tables)

# .clear() 方法：清除 MetaData 中所有注册的表，注意，这个操作不会影响数据库
Base.metadata.clear()

# .remove(table) 方法：清除MetaData指定的表
# 上面的 UserV1 类如果没有 __table_args__ = {'extend_existing': True} 的话，就只能生成并注册一次，除非使用上面的 clear() 方法清除
Base.metadata.remove(UserV1.__table__)

# .create_all() 方法：在数据库中创建 MetaData中注册的所有表，它有一个 tables= 参数(list of Table 对象)，可以指定创建的表，
# 默认下，只会创建不存在的表，
# Base.metadata.create_all(engine)
Base.metadata.create_all(bind=engine, tables=[UserV1.__table__])

# .drop_all() 方法：清除数据库中所有已创建的表对象，也可以接受一个 tables 参数
Base.metadata.drop_all(bind=engine)

# .reflect() 方法：从数据库中加载所有的表定义 ---- KEY
Base.metadata.reflect(bind=engine)
db_tables = Base.metadata.tables


# 2.2 ------- 传统定义(Classical Mapping) ---------
def P2_2_Classical():
    pass

# 下面这种方式是 从 1.3 版本就有的，1.4 版本中提供了使用 registry() 的方式，不过我觉得更麻烦
# 手动创建 MetaData 对象
# metadata_obj = MetaData()
# 或者使用上面的 Base 对象的 metadata 属性获取已有的 MetaData
metadata_obj = Base.metadata

# 定义表
UserV2 = Table(
    "user_v2",
    metadata_obj,
    Column("id", Integer, primary_key=True),
    Column("name", String(64)),
    Column("gender", String(64)),
    Column("age", Integer),
    Column("province", String(64))
)
# 创建表，这里 UserV2 已经是 Table 对象了
metadata_obj.create_all(engine, tables=[UserV2])

print(metadata_obj.tables)


# --------------  3. SQL CRUD 操作  --------------
# 使用 SQL Expression Language 1.x API 进行增删查改操作
def P3_SQL_CRUD():
    pass

def P3_1_ADD():
    # 生成一个插入语句
    ins = UserV2.insert()
    # 查看插入语句
    print(str(ins))
    # 查看编译的插入值
    print(ins.compile().params)

    # 限制使用哪些值
    ins = UserV2.insert().values(name="jack", gender="male")
    print(str(ins))
    print(ins.compile().params)

    # 实际执行
    with engine.connect() as conn:
        result = conn.execute(ins)

    print(result.__class__)
    # <class 'sqlalchemy.engine.cursor.LegacyCursorResult'>


def P3_2_Query():
    # SELECT 查询
    sel = select(UserV2)
    print(sel)
    with engine.connect() as conn:
        result = conn.execute(sel)
    for row in result:
        print(row)
    print(row.__class__)
    # <class 'sqlalchemy.engine.row.LegacyRow'>
    print(row[1])
    print(row.name)
    print(row['name'])

    # 使用产品表进行演示
    products = db_tables['products']
    # products 是一个 Table 对象，它是 Classical Mapping 的底层实现
    print(products.__class__)
    # 通过 .columns （可以缩写为 .c）属性获取所有的列
    print(list(products.columns))
    print(list(products.c))
    # 获取单个列
    print(products.c.prod_name)
    print(products.c['prod_name'])

    s1 = select(products.c.prod_id, products.c.vend_id, products.c.prod_name, products.c.prod_price)\
        .where(products.c.vend_id == '1001')\
        .order_by(products.c.prod_price.desc())
    print(s1)
    # print(s1.compile().params)
    with engine.connect() as conn:
        result = conn.execute(s1)
        for row in result:
            print(row)

    s2 = select(products.c.vend_id, func.sum(products.c.prod_price).label("price_sum")).group_by(products.c.vend_id)
    print(s2)
    # print(s2.compile().params)
    with engine.connect() as conn:
        result = conn.execute(s2)
        for row in result:
            print(row)


# --------------  4. ORM CRUD 操作  --------------
# 使用 ORM 1.X API 进行增删查改操作
def P4_ORM_CRUD():
    pass

Session = sessionmaker(bind=engine)
session = Session()


# --------- 4.1 插入对象 ------------
def P4_1_Add():
    # 创建一个 UserV1 类的对象，对应于表中的一行记录
    u1 = UserV1(name='Jane', gender='female', age=18, province='anhui')
    print(u1.name)
    print(u1.gender)
    # 插入数据库
    session.add(u1)
    session.add_all([UserV1(name='wendy', gender='female', age=22, province='hebei'),
                     UserV1(name='daniel', gender='male', age=28, province='anhui')])
    # 提交变更
    session.commit()

# --------- 4.2 查询 ------------
def P4_1_Query():
    # 使用产品表进行演示
    products = db_tables['products']
    # products 是一个 Table 对象，它是 Classical Mapping 的底层实现
    print(products.__class__)
    # 通过 .columns （可以缩写为 .c）属性获取所有的列
    print(list(products.columns))
    print(list(products.c))
    # 获取单个列
    print(products.c.prod_name)
    print(products.c['prod_name'])

    # Query 对象是使用SQLAlchemy-ORM进行查询的主要对象，它有如下常用的方法：
    # .all(), .one(), first() 等返回指定数量结果
    # .order_by(), .limit(), .offset()
    # .count(), .distinct(), .group_by(),
    # .filter(), .filter_by(), .where(), .having()
    # .join(), .outerjoin()
    # .union(), .union_all()
    # .statement：返回Query对应的SQL语句形式
    # .subguery()：返回当前Query对象对于的SQL语句，但是依旧封装为Query对象，通常用于子查询

    # 这里传入的 products 是 Table 对象，不过通常传入的，应该是 Base 的子类
    res1 = session.query(products).order_by(products.c.vend_id.desc())
    # 打印SQL
    print(res1)
    print(res1.statement)
    # 一定要在打印之后执行 all() 方法
    for row in res1.all():
        print(row)
    print(row.__class__)
    # <class 'sqlalchemy.engine.row.Row'>
    print(row[1])
    print(row.vend_id)
    print(row['vend_id'])

    res2 = session.query(products).where(products.c.vend_id == '1003')
    print(res2)
    print(res2.statement)
    # 打印实际包含参数的SQL语句
    print(res2.statement.compile(compile_kwargs={"literal_binds": True}))
    for row in res2.all():
        print(row)

    res3 = session.query(products.c.vend_id, func.sum(products.c.prod_price).label('prod_sum')).group_by(products.c.vend_id)
    print(res3)
    for row in res3.all():
        print(row)
    print(row.prod_sum)

    # 注意，对于 delete 的操作，上面的这种打印方式就不行了


# ---------------------------------------------------------
# 从 1.4 版本起，将 Core 和 ORM 的查询方式进行了整合，倾向于统一使用 CORE 风格的API进行查询操作 —— 这也是 2.x 版本的最大改动之一
def P5_Unify_Query():
    # 从 1.4 版本起， select() 函数支持两种方式：
    # 1. 传入 Table 对象进行查询 —— 这是 SQL Expression Language，也就是 Core 的方式
    # 2. 传入 Base 类的子类对象进行查询 —— 这是 ORM 的方式

    # UserV1 是 ORM 对象，可以直接访问对应的属性
    s1 = select(UserV1).where(UserV1.name == 'daniel')
    print(s1)
    print(s1.compile(compile_kwargs={"literal_binds": True}))
    # 使用 session.execute() 执行查询
    res1 = session.execute(s1).all()
    # print(res1.__class__)
    for row1 in res1:
        print(row1)
    # 返回的是 Row 对象
    print(row1.__class__)
    # <class 'sqlalchemy.engine.row.Row'>
    print(row1)  # 打印出来是一个元组，第一个元素是 User 对象
    # (< User(name=daniel, gender=male, age=28, province='anhui') >,)
    print(row1[0])
    # <User(name=daniel, gender=male, age=28, province='anhui')>
    print(row1[0].__class__)
    # <class '__main__.UserV1'>

    # UserV2 是 Table 对象，访问属性时，需要通过 .c 来做一下中转
    s2 = select(UserV2).where(UserV2.c.name == 'daniel')
    print(s2)
    print(s2.compile(compile_kwargs={"literal_binds": True}))
    # 使用 Connection.execute() 执行查询
    with engine.connect() as conn:
        res2 = conn.execute(s2).all()
        # print(res2.__class__)
    for row2 in res2:
        print(row2)
    # 返回的是 LegacyRow
    print(row2.__class__)
    # <class 'sqlalchemy.engine.row.LegacyRow'>
    print(row2)  # 打印出来 就直接是值
    # (1, 'daniel', 'male', 26, 'anhui')



