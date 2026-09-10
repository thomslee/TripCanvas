# -*- coding: utf-8 -*-
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, DECIMAL, JSON
from ..database import Base


class Poi(Base):
    """POI 池：多源聚合、人工标注。"""
    __tablename__ = "pois"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(String(64), nullable=False, index=True)
    poi_type = Column(String(16), nullable=False, index=True)  # attraction/hotel/restaurant
    name = Column(String(128), nullable=False)
    address = Column(String(255), nullable=True)
    open_hours = Column(String(128), nullable=True)
    ticket_price = Column(String(64), nullable=True)  # 票价描述：免费 / ¥40 / 人均 ¥80
    rating = Column(DECIMAL(3, 1), nullable=True)
    price_level = Column(String(16), nullable=True)
    tags = Column(String(255), nullable=True)  # 逗号分隔
    lat = Column(DECIMAL(10, 7), nullable=True)
    lng = Column(DECIMAL(10, 7), nullable=True)
    source = Column(String(32), nullable=True)  # 数据源标识（seed=内置示例，gaode=高德）
    created_at = Column(DateTime, default=datetime.now)


class AiRecommendation(Base):
    """AI 推荐版本留痕，支持对比与复盘。"""
    __tablename__ = "ai_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    params_snapshot = Column(JSON, nullable=True)
    result_snapshot = Column(JSON, nullable=True)
    diff_summary = Column(String(512), nullable=True)
    accepted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.now)


class UserFeedback(Base):
    """反馈闭环，反哺 POI 评分与推荐权重。"""
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_id = Column(Integer, ForeignKey("itinerary_nodes.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(16), nullable=False)  # like/dislike/skip
    created_at = Column(DateTime, default=datetime.now)
