"""
SQLModel练习
"""
import asyncio
from urllib import parse
from pydantic import model_validator
from sqlmodel import SQLModel, Field, create_engine, Session, select, or_, desc
from sqlmodel._compat import SQLModelConfig
# 截止到 SQLModel 0.0.24 版本， ext 模块下只有 asyncio，里面也只有 session.py 文件，该文件里只有一个 AsyncSession 对象
from sqlmodel.ext.asyncio.session import AsyncSession
# 异步使用，目前还是需要调用 sqlalchemy 的组件
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker, AsyncSession, AsyncConnection
from sqlalchemy import create_engine as create_engine_origin, select as select_origin
from sqlalchemy.orm import Session as Session_origin
from sqlalchemy import Column, String, Integer, DateTime, Boolean

from typing import List
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse


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
# 下面这个是同步引擎——SQLModel提供的封装
engine = create_engine(url=db_url, echo=True)

# sqlalchemy 的原始引擎对象
engine_origin = create_engine_origin(url=db_url, echo=True)

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
    # Field 对象是对 Pydantic 的 Field 对象的封装，增加了 sqlalchemy 字段设置的支持，大部分 Pydantic Field 对象的参数都可以使用
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
    age: int | None = Field(default=None, nullable=True, sa_column_kwargs={'comment': '英雄年龄'}, ge=0, le=1000)

    # 可以看出，sa_type 设置的 String 覆盖了类型提示里的 int
    # 这里还需要注意的是，String 是怎么传入 Column() 的，这里就要怎么写，对于String类型来说，length 参数不能少
    # gender: int | None = Field(default=None, nullable=True, sa_type=String(length=50), sa_column_kwargs={'comment': '性别'})
    # 也可以直接设置 sa_column，传入 Column() 的实例对象
    # address: int | None = Field(default=None, sa_column=Column(String(64), nullable=True, comment='地址'))
    # 上面两个字段 类型提示 故意写错了，虽然在数据库里没有问题，不过会对 pydantic 的校验产生影响，所以使用下面正确方式
    gender: str | None = Field(default=None, nullable=True, sa_type=String(length=50), sa_column_kwargs={'comment': '性别'})
    address: str | None = Field(default=None, sa_column=Column(String(64), nullable=True, comment='地址'))

    # SQLModel 使用时，一旦上面定义类时设置了 table=True，那么 Pydantic 提供下面的校验方式就不会被执行 ！！！
    # Pydantic的校验配置
    @model_validator(mode='after')
    def check_user_name(self):
        print(f"check user name for {self.name}")
        self.name = self.name + "-suffix"
        return self

    # 下面这配置不行，会导致重复执行validator
    # model_config = SQLModelConfig(from_attributes=True, validate_assignment=True)


# **************************** 校验功能  ****************************
def model_validation():
    # SQLModel 定义类时如果使用了 table=True，那么 Pydantic 提供的校验功能就失效了 ！！！
    h1 = Hero(name="Deadpond", secret_name="Dive Wilson", age=20, gender='male')
    # 不会报错 ！！！
    h2 = Hero(name="InvalidAge", age=-1, gender='male')
    # 除非使用下面的方式手动执行校验
    Hero.model_validate(h1)
    Hero.model_validate(h2)
    # 关于这一点，一开始我以为是Bug，参考如下Issue：
    # - [Why does a SQLModel class with table=True not validate data ?](https://github.com/fastapi/sqlmodel/issues/453)
    # - [Pydantic Validators does not raise ValueError if conditions are not met](https://github.com/fastapi/sqlmodel/issues/134)
    # - [SQLModel seems to disable @model_validator when initialized with table=true](https://github.com/fastapi/sqlmodel/discussions/805
    # - [Ensure that type checks are executed when setting table=True](https://github.com/fastapi/sqlmodel/pull/1041)
    # 但是后来我发现似乎作者是有意这么设计的，合理的使用方式应该参考官方文档 [Multiple Models with FastAPI](https://sqlmodel.tiangolo.com/tutorial/fastapi/multiple-models/)
    # 使用 多个Model + 继承 的方式来隔离不同的使用场景


# **************************** 同步使用方式  ****************************
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
    # ----------------------------
    # 用原生引擎试试 ——— 也是可以的
    # session = Session(engine_origin)
    # ----------------------------
    # 用原生引擎 + 原生Session ——— 也没问题
    # session = Session_origin(engine_origin)
    # ----------------------------
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


def select_heroes_mix():
    """ 检查下 SQLModel 和 sqlalchemy 的混合使用 """
    # 使用原生引擎查询 —— 也可以
    with Session(engine_origin) as session:
        statement = select(Hero)
        results = session.exec(statement)
        for hero in results:
            print(hero)

    # 使用原生引擎 + 原生Session 查询 —— 没问题
    with Session_origin(engine_origin) as session:
        statement = select(Hero)
        # 不过方法名称需要换一下
        results = session.execute(statement)
        for hero in results:
            print(hero)

    # 使用原生引擎 + 原生Session + 原生 select 查询 —— 还是没问题
    with Session(engine_origin) as session:
        statement = select_origin(Hero)
        # 不过方法名称需要换一下
        results = session.execute(statement)
        for hero in results:
            print(hero)

def main():
    print(">>>>>>> run main")
    init_db()
    print("===============================================")
    add_heroes()
    print("===============================================")
    select_heroes()
    select_heroes_mix()


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


# **************************** 结合FastAPI使用 ****************************
app = FastAPI()

@app.get("/heroes", response_model=List[Hero])
def list_hero():
    result: List[Hero] = []
    with Session(engine) as session:
        statement = select(Hero)
        results = session.exec(statement)
        for hero in results:
            print(hero)
            result.append(hero)
    return result

@app.get("/hero/{uid}", response_model=Hero)
def get_hero(uid: int):
    with Session(engine) as session:
        statement = select(Hero).where(Hero.uid == uid)
        result = session.exec(statement)
        hero = result.one_or_none()
    return hero


@app.post("/hero/new", response_class=JSONResponse, response_model=Hero)
def create_hero(hero: Hero):
    # 检查 Hero 的入参校验
    with Session(engine) as session:
        session.add(hero)
        session.commit()
        session.refresh(hero)
    return hero


if __name__ == '__main__':
    main()
    asyncio.run(main_async())

    host = "localhost"
    # host = "10.8.6.203"
    port = 8100
    uvicorn.run("sqlmodel_practice:app", host=host, port=port, log_level="info")

