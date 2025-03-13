"""
SQLAlchemy异步使用，以2.0为例
"""
import asyncio
from urllib import parse
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, async_scoped_session, AsyncEngine, \
    AsyncSession, AsyncConnection
from sqlalchemy import MetaData, Table, Column, Integer, String, ForeignKey, CursorResult, text
from sqlalchemy.orm import sessionmaker, declarative_base, registry
from sqlalchemy.future import select

# --------------- 1. 连接数据库 ---------------
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
# 数据库驱动改为 aiomysql
db_url = 'mysql+aiomysql://{user}:{passwd}@{host}:{port}/{database}'.format(**mysql_conf)
async_engine = create_async_engine(url=db_url, echo=True)


# ------------ 2. 使用 Connection -------------------
def P1_Connection():
    pass

async def async_connection():
    async with async_engine.begin() as conn:
        # print(type(conn))
        # 类型是AsyncConnection
        # select a Result, which will be delivered with buffered results
        result1 = await conn.execute(text("select * from customers"))
        # print(type(result1))
        # sqlalchemy.engine.cursor.CursorResult  # 这个对象不是异步对象
        # print(result1.fetchall())
        for row in result1:
            print(row)

    async with async_engine.connect() as conn:
        result2 = await conn.execute(text("select * from products"))
        # print(result2.fetchall())
        for row in result2:
            print(row)

    # for AsyncEngine created in function scope, close and clean-up pooled connections
    await async_engine.dispose()

# asyncio.run(async_connection())


# ------------ 2. Core 使用 -------------------
def P2_Core_Usage():
    pass


metadata_core = MetaData()

# 定义表
user_core = Table(
    "user_core",  # 表名称
    metadata_core,
    # 使用 Column 对象来定义列，并设置列的具体类型
    Column("uid", Integer, primary_key=True, autoincrement=True),
    Column("name", String(63), nullable=False),
    Column("gender", String(63)),
    Column("age", Integer),
    # 表的注释
    comment="用户表-core",
    # 指定 schema
    schema="crashcourse",
    # 是否覆盖已有的表
    extend_existing=True,
    # 建表的其他参数，依据具体的数据库类型而定
    mysql_engine="InnoDB"
)

async def async_core_usage():
    async with async_engine.begin() as conn:
        # print(type(conn))  # AsyncConnection
        # 创建表
        # 下面这一句是一个同步调用，需要封装成异步调用
        # metadata_core.create_all(bind=conn, tables=[user_core], checkfirst=True)
        # 异步调用时，第一个参数 bind 由 run_sync 方法传入，不需要自己传入
        res = await conn.run_sync(metadata_core.create_all, tables=[user_core], checkfirst=True)
        print(res)
        print('-------------------------------')

        # 插入数据
        res: CursorResult = await conn.execute(
            user_core.insert(),
            [{"name": "daniel", "gender": "male", "age": 31}, {"name": "jane", "gender": "female", "age": 28}]
        )
        # print(type(res))
        # 不返回结果，不能调用
        # print(res.fetchall())
        # print(res.scalar())
        print('-------------------------------')

    # 查询数据
    async with async_engine.connect() as conn:
        result: CursorResult = await conn.execute(select(user_core).where(user_core.c.name == "daniel"))
        # print(result.fetchall())
        for row in result:
            print(row)

    await async_engine.dispose()


# asyncio.run(async_core_usage())



# ------------ 3. ORM 使用 -------------------
def P3_ORM_Usage():
    pass


Base = declarative_base()


class UserORM(Base):
    __tablename__ = 'user_orm'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'comment': '用户表-ORM',
        'extend_existing': True
    }
    # 定义表的各个字段
    uid = Column(Integer, primary_key=True, autoincrement=True)  # 主键
    name = Column(String(64), nullable=False)
    gender = Column(String(64), nullable=True)
    age = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<User(name={self.name}, gender={self.gender}, age={self.age}')>"


async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(async_engine, expire_on_commit=False)
session = async_session()

async def async_orm_usage():

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[UserORM], checkfirst=True)


        async with async_session() as session:
            async with session.begin():
                session.add_all()

