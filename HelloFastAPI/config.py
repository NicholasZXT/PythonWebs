from pydantic import Field
# from pydantic import BaseSettings  # Pydantic-V2.x开始，这个对象移动到了 pydantic-settings 包中
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict
from functools import lru_cache
import os


class Settings(BaseSettings):
    ENV_NAME: str = None
    DEBUG: bool = False
    SWAGGER_UI_ENABLE: bool = False
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = None
    MYSQL_PASSWORD: str = None
    MYSQL_DB: str = None
    # 下面两个变量需要放在 __init__ 方法里初始化，因为这些变量需要用到其他变量的值，并且它们的值必须要允许 None
    DB_URL: str | None = None
    DB_URL_ASYNC: str | None = None
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 60 * 5
    AUTHORIZED_USERS: Dict = {
        'admin': {'passwd': 'admin', 'roles': ['admin', 'others']},
        'yourself': {'passwd': 'people', 'roles': ['others']},
    }

    def __init__(self, *args, **kwargs):
        # 必须要先调用 父类的 __init__ 方法，才能从环境变量里获取值
        super().__init__(*args, **kwargs)
        self.DB_URL = f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
        self.DB_URL_ASYNC = f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"


@lru_cache(maxsize=1)
def get_settings(env: str) -> Settings:
    env_path = f"envs/{env}.env"
    print(f"Reading environment variables from {env_path}")
    settings = Settings(_env_file=env_path)
    return settings


# 只能先从环境变量 FASTAPI_ENV 里获取要使用的配置文件名
fastapi_env = os.getenv("FASTAPI_ENV", "dev").lower()
settings = get_settings(fastapi_env)


if __name__ == '__main__':
    settings = get_settings('dev')
    # settings = get_settings('prod')
    print(settings.model_dump_json())
