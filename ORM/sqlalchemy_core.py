"""
练习 SQL Alchemy 的 Core，以 1.4 版本为例
2.0 版本 Core 的使用语法基本没有变化。
"""
import logging
from urllib import parse
from sqlalchemy import create_engine, inspect
from sqlalchemy import MetaData, Table, Column, Integer, String, ForeignKey
from sqlalchemy.sql.expression import text, insert, select, func

# 设置日志级别
logging.basicConfig()
logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)

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
# engine = create_engine(db_url)
engine = create_engine(db_url, echo=True)


# --------------- 定义表 ---------------
def P1_Def_Tables():
    pass

# 先创建一个 MetaData 对象
metadata_obj = MetaData()

# 定义表
user = Table(
    "user_core",  # 表名称
    # 必须要绑定到一个 MetaData 对象上
    metadata_obj,
    # 使用 Column 对象来定义列，并设置列的具体类型
    Column("uid", Integer, primary_key=True, autoincrement=True),
    Column("name", String(63), nullable=False),
    Column("fullname", String(63), nullable=False),
    Column("gender", String(63)),
    # 表的注释
    comment="用户表-core",
    # 指定 schema
    # schema="school",
    # 是否覆盖已有的表
    extend_existing=True,
    # 建表的其他参数，依据具体的数据库类型而定
    mysql_engine="InnoDB"
)

# 显示 MetaData 中所有注册的表
# for t in metadata_obj.sorted_tables:
#     print(t.name)

# 创建表
# 创建单个表
# user.create(bind=engine)
# 创建 metadata 中的所有表
# metadata_obj.create_all(bind=engine)

# 删除表
# 删除单个表
# user.drop(bind=engine)
# 删除 metadata 所有表
# metadata_obj.drop_all(bind=engine)

# --------------- 增删查改 ---------------
def P2_CRUD():
    """增删查改"""
    pass

def P2_1_Add():
    # 创建一个 insert 语句，不过没有具体插入值
    ins1 = user.insert()
    # 打印出来
    print(ins1)
    # 查看类型，是一个 Insert 对象
    print(type(ins1))
    # <class 'sqlalchemy.sql.dml.Insert'>

    # 指定插入值，这里只用了两列值
    ins2 = user.insert().values(name="jack", fullname="Jack Jones")
    # 并没有显示插入值，只显示了占位符
    print(ins2)
    # 查看具体的插入参数
    print(ins2.compile().params)
    # 查看编译后的实际插入语句
    print(ins2.compile(compile_kwargs={"literal_binds": True}))

    # 或者使用 insert 函数 —— 推荐使用这种方式，更符合SQL的原始写法
    ins3 = insert(user).values(name="rose", fullname="rose little")
    print(type(ins3))   # 得到的也是 Insert 对象
    # <class 'sqlalchemy.sql.dml.Insert'>
    print(ins3)
    print(ins3.compile().params)
    print(ins3.compile(compile_kwargs={"literal_binds": True}))

    # 具体执行
    # 1. 手动管理连接并执行
    # conn = engine.connect()
    # res = conn.execute(ins2)
    # conn.commit()  # 必须要手动 commit
    # conn.close()
    # 2. 使用 with 上下文
    # with engine.connect() as conn:
    #     res = conn.execute(ins2)
    #     conn.commit()  # 也必须要手动提交，否则会自动回滚
    #     print(res)  # 插入语句不会返回内容，所以res为空
    # 3. 或者使用下面的with上下文，就不用手动commit了 —— 推荐
    with engine.begin() as conn:
        res = conn.execute(ins2)

    # 执行多个语句
    with engine.begin() as conn:
        res = conn.execute(
            ins1,
            [
                {"uid": 1, "name": "daniel", "fullname": "daniel zhang", "gender": "male"},
                {"uid": 2, "name": "jane", "fullname": "jane zhou", "gender": "female"},
            ]
        )


def P2_2_Query():
    # select语句
    s1 = select(user)
    print(s1)

    with engine.begin() as conn:
        res = conn.execute(s1)
        # Connection 对象的 execute 方法的返回值始终是一个 CursorResult 对象，代表底层的cursor
        # CursorResult 和 LegacyCursorResult 对象代替了1.3版本中的 ResultProxy 对象
        print(type(res))
        # <class 'sqlalchemy.engine.cursor.CursorResult'>
        # CursorResult 对象通过 Row 对象来封装每一行数据，.all(), .fetchall() 等方法返回的都是 Row 对象的列表或者单独的元素
        for row in res:
            print(row)
        # row 的类型
        print(type(row))
        # <class 'sqlalchemy.engine.row.Row'>
        # Row 对象类似于namedtuple，支持通过 Row.attr 的方式来直接访问其中的值

    # 另一种访问 结果的方式
    with engine.begin() as conn:
        res = conn.execute(s1)
        for uid, name, fullname, gender in res:
            print(f"uid: {uid}, name: {name}, fullname: {fullname}, gender: {gender}")

    # 指定返回列 + 排序 + 限制结果
    s2 = select(user.c.uid, user.c.name, user.c.gender) \
          .where(user.c.gender == 'female') \
          .order_by(user.c.uid.asc()) \
          .limit(2)
    # print(s2)
    print(s2.compile(compile_kwargs={"literal_binds": True}))
    with engine.begin() as conn:
        res = conn.execute(s2)
        for uid, name, gender in res:
            print(f"uid: {uid}, name: {name}, gender: {gender}")

    # 分组聚合
    s3 = select(user.c.gender,
                func.count(user.c.uid).label('cnt'),
                func.count(user.c.gender.distinct()).label('unique_cnt')
                ) \
          .group_by(user.c.gender)
    print(s3)
    with engine.begin() as conn:
        res = conn.execute(s3)
        for gender, cnt, unique_cnt in res:
            print(f"gender: {gender}, cnt: {cnt}, unique_cnt: {unique_cnt}")


def P2_3_Delete():
    pass


def P2_4_Update():
    pass


if __name__ == '__main__':
    ins = user.insert().values(name="jack", fullname="Jack Jones")
    # with engine.begin() as conn:
    #     res = conn.execute(ins)
