# -*- coding: utf-8 -*-
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime
from ..database import Base


class AppSetting(Base):
    """应用设置：大模型 API、高德 Key 等外部连接配置，key-value 存储。"""
    __tablename__ = "app_settings"

    skey = Column(String(64), primary_key=True)
    svalue = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
