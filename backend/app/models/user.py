# -*- coding: utf-8 -*-
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nickname = Column(String(64), nullable=True)
    preferences = Column(JSON, nullable=True)  # 兴趣/节奏/预算/人数
    created_at = Column(DateTime, default=datetime.now)
