# -*- coding: utf-8 -*-
"""应用配置：支持 .env 覆盖，默认本机 MySQL。"""
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "途迹 TripCanvas"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # 数据库（默认本机 MySQL8，root/123456）
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "123456"
    DB_NAME: str = "trip_canvas"

    # Redis（M3 AI 任务队列再用，先留配置）
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"


settings = Settings()
