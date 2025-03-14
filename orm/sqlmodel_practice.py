"""
SQLModel练习
"""
import asyncio
from urllib import parse
from sqlmodel import SQLModel, Field, create_engine, Session, select, or_, desc
# 截止到 SQLModel 0.0.24 版本， ext 模块下只有 asyncio，里面也只有 session.py 文件，该文件里只有一个 AsyncSession 对象
from sqlmodel.ext.asyncio.session import AsyncSession
# 异步使用，目前还是需要调用 sqlalchemy 的组件
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker, AsyncSession, AsyncConnection
from sqlalchemy import Column, String, Integer, DateTime, Boolean


# --------------- 连接数据库 ---------------
mysql_conf = {
    'host': 'localhost',
    'user': 'root',
    # 'passwd': 'mysql@2018',
    # 'passwd': 'mysql2020',
    'passwd': 'mysql2022',
    'port': 3306,
    'database': 'hello_fastapi'
}
mysql_conf['passwd'] = parse.quote_plus(mysql_conf['passwd'])
db_url = 'mysql+pymysql://{user}:{passwd}@{host}:{port}/{database}'.format(**mysql_conf)
db_url_async = 'mysql+aiomysql://{user}:{passwd}@{host}:{port}/{database}'.format(**mysql_conf)
# 下面这个是同步引擎
engine = create_engine(url=db_url, echo=True)

# 异步引擎和异步Session对象
async_engine: AsyncEngine = create_async_engine(url=db_url_async)
SessionLocalAsync: async_sessionmaker[AsyncSession] = async_sessionmaker(bind=async_engine, expire_on_commit=False)


class Hero(SQLModel, table=True):
    __tablename__ = 'hero'
    __table_args__ = {
        'extend_existing': True,
        'mysql_engine': 'InnoDB',
        'comment': 'Hero表',
    }
    # SQLModel 会从类型提示里获取类型，并转换成 sqlalchemy 里的对应类型，如果找不到，就会抛异常
    # 所以一般来说不需要在 Field 里指定类型，但是可以配置对应类型的参数
    uid: int | None = Field(
        default=None,
        primary_key=True,
        # unique=True, nullable=False,
        # 可以自己直接设置sqlalchemy的字段类型，这样就不会从类型提示里获取
        sa_type=Integer,
        # Columns 的其他参数需要通过字典形式传入
        sa_column_kwargs={'comment': '主键', 'autoincrement': True}
    )
    name: str = Field(max_length=50, nullable=False, sa_column_kwargs={'comment': '英雄名称'})
    secret_name: str = Field(max_length=50, nullable=True, sa_column_kwargs={'comment': '英雄真实名称'})
    age: int | None = Field(default=None, nullable=True, sa_column_kwargs={'comment': '英雄年龄'})
    # 可以看出，sa_type 设置的 String 覆盖了类型提示里的 int
    # 这里还需要注意的是，String 是怎么传入 Column() 的，这里就要怎么写，对于String类型来说，length 参数不能少
    gender: int | None = Field(default=None, nullable=True, sa_type=String(length=50), sa_column_kwargs={'comment': '性别'})
    # 也可以直接设置 sa_column，传入 Column() 的实例对象
    address: int | None = Field(default=None, sa_column=Column(String(64), nullable=True, comment='地址'))


# ---------------- 同步使用方式 -----------------
def init_db():
    print(">>>>>>> init heroes")
    SQLModel.metadata.drop_all(engine, tables=[Hero.__table__], checkfirst=True)
    SQLModel.metadata.create_all(engine, tables=[Hero.__table__], checkfirst=True)


def add_heroes():
    print(">>>>>>> adding heroes")
    hero_1 = Hero(name="Deadpond", secret_name="Dive Wilson")
    hero_2 = Hero(name="Spider-Boy", secret_name="Pedro Parqueador")
    hero_3 = Hero(name="Rusty-Man", secret_name="Tommy Sharp", age=48)
    # 下面这个 Session 对象是同步的
    session = Session(engine)
    session.add(hero_1)
    session.add(hero_2)
    session.add(hero_3)
    session.commit()
    session.close()


def select_heroes():
    print(">>>>>>> selecting heroes")
    with Session(engine) as session:
        statement = select(Hero)
        results = session.exec(statement)
        for hero in results:
            print(hero)

        print("------------------------------------------")
        statement = select(Hero).where(Hero.name == "Deadpond")
        results = session.exec(statement)
        for hero in results:
            print(hero)

        print("------------------------------------------")
        statement = select(Hero).where(Hero.age >= 35).where(Hero.age < 40)
        results = session.exec(statement)
        for hero in results:
            print(hero)

        print("------------------------------------------")
        statement = select(Hero).where(or_(Hero.age <= 35, Hero.age > 90))
        results = session.exec(statement)
        for hero in results:
            print(hero)

def main():
    print(">>>>>>> run main")
    init_db()
    print("===============================================")
    add_heroes()
    print("===============================================")
    select_heroes()


# **************************** 异步使用方式 ****************************
# 异步使用，目前还需要调用 sqlalchemy 的异步API
async def init_db_async():
    print(">>>>>>> init heroes")
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all, checkfirst=True)
    await async_engine.dispose()

async def add_heroes_async():
    hero_1 = Hero(name="Deadpond", secret_name="Dive Wilson", age=30, gender="male")
    hero_2 = Hero(name="Spider-Boy", secret_name="Pedro Parqueador", age=30, gender="male")
    hero_3 = Hero(name="Rusty-Man", secret_name="Tommy Sharp", age=48)

    print(">>>>>>> adding heroes")
    async with SessionLocalAsync() as session:
        session.add_all([hero_1, hero_2, hero_3])
        # 下面这句不能少
        await session.commit()
    await async_engine.dispose()

async def select_heroes_async():
    print(">>>>>>> selecting heroes")
    async with SessionLocalAsync() as session:
        # 注意，这里的 select 是SQLModel 封装的
        statement = select(Hero).where(or_(Hero.age <= 35, Hero.age > 90))
        results = await session.execute(statement)
        for hero in results:
            print(hero)
    await async_engine.dispose()

async def main_async():
    print(">>>>>>> run main_async")
    await init_db_async()
    print("===============================================")
    await add_heroes_async()
    print("===============================================")
    await select_heroes_async()

if __name__ == '__main__':
    main()
    asyncio.run(main_async())

