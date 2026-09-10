# -*- coding: utf-8 -*-
"""初始化数据库：建库 + 建表。用法：.venv\\Scripts\\python init_db.py"""
import pymysql
from sqlalchemy import create_engine, text

from app.config import settings
from app.database import Base
import app.models  # noqa: F401  注册全部模型

# 1) 建库（UTF8MB4）
conn = pymysql.connect(
    host=settings.DB_HOST, port=settings.DB_PORT,
    user=settings.DB_USER, password=settings.DB_PASSWORD,
    charset="utf8mb4",
)
try:
    with conn.cursor() as cur:
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{settings.DB_NAME}` "
            "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    conn.commit()
finally:
    conn.close()

# 2) 建表
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
Base.metadata.create_all(engine)

with engine.connect() as c:
    tables = c.execute(text("SHOW TABLES")).fetchall()
print("建表完成：", [t[0] for t in tables])
