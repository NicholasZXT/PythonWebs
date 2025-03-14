import asyncio
from typing import AsyncGenerator
from sqlalchemy import create_engine, Engine, Connection, MetaData, Table, Column
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine, AsyncSession, AsyncConnection

from config import settings

# SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"
SQLALCHEMY_DATABASE_URL = settings.DB_URL
Base = declarative_base()

# 同步引擎和Session对象
engine: Engine = create_engine(url=SQLALCHEMY_DATABASE_URL)
SessionLocal: sessionmaker[Session] = sessionmaker(bind=engine, autocommit=True, autoflush=False)

# 异步引擎和异步Session对象
async_engine: AsyncEngine = create_async_engine(url=SQLALCHEMY_DATABASE_URL)
SessionLocalAsync: async_sessionmaker[AsyncSession] = async_sessionmaker(bind=async_engine, expire_on_commit=False)

def init_db_tables():
    Base.metadata.create_all(bind=engine, checkfirst=True)

async def init_db_tables_async():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

# 用于获取Session的依赖函数
def get_db_session() -> AsyncGenerator[Session]:
    db = SessionLocal()
    try:
        yield db
    # 在依赖中使用yield时，yield之后的代码会在每次请求对应的视图函数返回 Response 之后执行，刚好用来做收尾工作
    finally:
        db.close()

async def get_db_session_async() -> AsyncGenerator[Session]:
    db = SessionLocalAsync()
    try:
        yield db
    finally:
        await db.close()
