"""
SQLAlchemy异步使用，以2.0为例
"""
import asyncio
from urllib import parse
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, async_scoped_session, AsyncEngine, \
    AsyncSession, AsyncConnection, AsyncSessionTransaction
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

# 这个MetaData对象可以被 Core 和 ORM 一起使用
metadata_obj = MetaData()
Base = declarative_base(metadata=metadata_obj)
# 异步Session对象工厂
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(async_engine, expire_on_commit=False)
# 通过上面的工厂对象来创建一个 AsyncSession 对象
async_session: AsyncSession = async_session_factory()
# AsyncSession 对象其实是同步对象 Session 的一个轻量代理


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
        # print(type(conn))
        # 类型是也AsyncConnection
        result2 = await conn.execute(text("select * from products"))
        # print(result2.fetchall())
        for row in result2:
            print(row)

    # 这一句必须要有，否则执行完会抛异常 ------ KEY
    # for AsyncEngine created in function scope, close and clean-up pooled connections
    await async_engine.dispose()


# ------------ 2. Core 使用 -------------------
def P2_Core_Usage():
    pass


# 定义表
user_core = Table(
    "user_core",  # 表名称
    metadata_obj,
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
        # print(type(conn))
        # AsyncConnection
        # 创建表
        # 下面这一句是一个同步调用，需要使用 AsyncConnection.run_sync 方法在异步环境下进行封装调用
        # metadata_obj.create_all(bind=conn, tables=[user_core], checkfirst=True)
        # 异步调用时，第一个参数 bind 由 run_sync 方法传入，不需要自己传入
        res = await conn.run_sync(metadata_obj.create_all, tables=[user_core], checkfirst=True)
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


# ------------ 3. ORM 使用 -------------------
def P3_ORM_Usage():
    pass


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


async def async_orm_usage():
    async with async_engine.begin() as conn:
        print(type(conn))
        # <class 'sqlalchemy.ext.asyncio.engine.AsyncConnection'>
        await conn.run_sync(Base.metadata.create_all, tables=[UserORM.__table__], checkfirst=True)

    # async_session 是 AsyncSession 对象，begin() 方法 返回的是 AsyncSessionTransaction 对象，自动管理事务
    async with async_session.begin() as session_transaction:
        print(type(session_transaction))
        # <class 'sqlalchemy.ext.asyncio.session.AsyncSessionTransaction'>
        user1 = UserORM(name="nicholas", gender="male", age=31)
        user2 = UserORM(name="alley", gender="female", age=30)
        # 注意，这里用的是 async_session，不是 session_transaction，
        async_session.add_all([user1, user2])
        # 对于 AsyncSessionTransaction 来说，这一句没必要，with 管理器会自动提交事务
        # await session_transaction.commit()

    #  async_sessionmaker 调用 __call__ 返回 AsyncSession 对象，也是使用 AsyncSession 的 __aenter__ 和 __aexit__ 方法
    # 需要手动管理事务
    async with async_session_factory() as session:
        print(type(session))
        # <class 'sqlalchemy.ext.asyncio.session.AsyncSession'>
        user1 = UserORM(name="xiaoming", gender="male", age=26)
        user2 = UserORM(name="xiaohong", gender="female", age=22)
        session.add_all([user1, user2])
        # 对于 AsyncSession 对象来说，必须要手动提交事务
        await session.commit()

    async with async_session_factory() as session:
        # print(type(session))
        # <class 'sqlalchemy.ext.asyncio.session.AsyncSession'>
        stmt = select(UserORM).where(UserORM.age > 18)
        # print(type(stmt))
        # <class 'sqlalchemy.sql.selectable.Select'>
        result = await session.execute(stmt)
        # print(type(result))
        # <class 'sqlalchemy.engine.result.ChunkedIteratorResult'>
        for row in result:
            print(row)

    await async_engine.dispose()


async def main_async():
    print("************* main_async **************")
    await async_connection()
    await async_core_usage()
    await async_orm_usage()


if __name__ == '__main__':
    asyncio.run(main_async())
