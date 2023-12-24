"""
练习 SQL Alchemy 的 Engine，以 1.4 版本为例
以下的查询表均来自《MySQL必知必会》附带的数据表，下载地址为:https://forta.com/books/0672327120/
"""
import logging
from urllib import parse
from sqlalchemy import create_engine, inspect
from sqlalchemy import MetaData, Table, Column, Integer, String, ForeignKey
from sqlalchemy.sql.expression import text, select, func
from sqlalchemy.orm import sessionmaker, declarative_base

# 设置日志级别
logging.basicConfig()
logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)

# --------------- 1. 连接数据库 ---------------
mysql_conf = {
    'host': 'localhost',
    'user': 'root',
    # 'passwd': 'mysql@2018',
    'passwd': 'mysql2020',
    # 'passwd': 'mysql2022',
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
# 可以通过 inspect() 查看 engine 的信息
insp = inspect(engine)

# 获取数据库里的表名称
# tables = engine.table_names()  # 这个方法在 1.14 版本中已经被废弃了
tables = insp.get_table_names()
print(tables)
# ['customers', 'orderitems', 'orders', 'productnotes', 'products', 'vendors']

# 有了`Engine`对象之后，可以通过如下两种方式执行对数据库的操作（[Working with Engines and Connections](https://docs.sqlalchemy.org/en/14/core/connections.html)）：
# 1. `Connection`对象：这个就是类似于 PEP-249 规范里定义的使用方式，通过`Connection`对象创建`Cursor`对象，执行SQL语句
# 2. `Session`对象：这个通常和SQLAlchemy-ORM配合使用

# ------------ 1 使用 Connection -------------------
def P1_Connection():
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


#  -------------- 2 使用 Session --------------
def P2_Session():
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
