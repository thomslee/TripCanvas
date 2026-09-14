# -*- coding: utf-8 -*-
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    nickname = Column(String(64), nullable=True)
    role = Column(String(16), nullable=False, default="user")  # admin / user
    gender = Column(String(8), nullable=True)  # 男/女/保密
    age = Column(Integer, nullable=True)
    identity = Column(String(16), nullable=True)  # 学生/职工/退休/其他
    preferences = Column(JSON, nullable=True)  # 兴趣标签，如["美食","购物","摄影"]
    created_at = Column(DateTime, default=datetime.now)
