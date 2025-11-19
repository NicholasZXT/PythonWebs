import os
from typing import Type
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    # 应用基本信息
    app_name: str = "Litestar Hello App"
    debug: bool = False

    # 服务地址：这里设置没啥用，因为 Litestar 没有提供 run() 方法，只能通过 Litestar CLI 启动或者 uvicorn 启动
    # host: str = "0.0.0.0"
    # port: int = 8100

    # 数据库
    db_url: str = "sqlite+aiosqlite:///./test.db"

    # JWT
    jwt_secret: str = "secret"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_seconds: int = 900  # 15 分钟

    model_config = SettingsConfigDict(
        env_file_encoding='utf-8',
        case_sensitive=False
    )

    @classmethod
    def from_env(cls: Type['AppSettings'], env: str) -> 'AppSettings':
        env_file = os.path.join('envs', f'{env}.env')
        if os.path.exists(env_file):
            return cls(_env_file=env_file)
        else:
            # raise FileNotFoundError(f"Environment file {env_file} not found!")
            print(f'Environment file {env_file} not found, using default settings.')
            return cls()


@lru_cache
def get_settings() -> AppSettings:
    app_settings = AppSettings.from_env(os.getenv('ENV_FILE', 'dev'))
    return app_settings


settings = get_settings()


if __name__ == '__main__':
    dev = AppSettings.from_env('dev')
    print(dev)
