from pydantic import Field
# from pydantic import BaseSettings  # 这个对象移动到了 pydantic-settings 包中
from pydantic_settings import BaseSettings
from typing import Dict

MYSQL_CONF = {
    'user': 'root',
    'passwd': 'mysql2022',
    'host': 'localhost',
    'port': 3306,
    'db': 'hello_fastapi'
}
class Settings(BaseSettings):
    DB_URL: str = "mysql+pymysql://{user}:{passwd}@{host}:{port}/{db}".format(**MYSQL_CONF)
    SECRET_KEY: str = "fastkey09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf68e8d3e7"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 60 * 10
    AUTHORIZED_USERS: Dict = {
        'admin': {'passwd': 'admin', 'roles': ['admin', 'others']},
        'yourself': {'passwd': 'people', 'roles': ['others']},
    }

settings = Settings()
