from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

# SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"
SQLALCHEMY_DATABASE_URL = settings.DB_URL

Base = declarative_base()
engine = create_engine(url=SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db_tables():
    Base.metadata.create_all(bind=engine)

# 用于获取Session的依赖函数
def get_db():
    db = SessionLocal()
    try:
        yield db
    # 在依赖中使用yield时，yield之后的代码会在每次请求对应的视图函数返回 Response 之后执行，刚好用来做收尾工作
    finally:
        db.close()
