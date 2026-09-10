# -*- coding: utf-8 -*-
from datetime import datetime, date, time
from sqlalchemy import Column, Integer, String, Date, Time, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from ..database import Base


class Trip(Base):
    """行程主表：一次旅程一张画布。"""
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # M1 免登录，可空
    title = Column(String(128), nullable=True)          # 自动生成，如「大理 4 天 3 晚」
    depart_city = Column(String(64), nullable=False)
    dest_city = Column(String(64), nullable=False)
    depart_date = Column(Date, nullable=False)          # 去程日期
    arrive_time = Column(Time, nullable=True)           # 去程到达时刻（可空）
    return_date = Column(Date, nullable=False)          # 返程日期
    depart_time = Column(Time, nullable=True)           # 返程起飞时刻（可空）
    total_days = Column(Integer, nullable=False, default=1)  # 旅行天数
    status = Column(String(16), nullable=False, default="draft")  # draft/planning/active/done
    preferences = Column(JSON, nullable=True)
    dest_cities = Column(JSON, nullable=True)   # 多城市目的地：[{city, days}, ...]；单城市=[{dest_city, total_days}]
    depart_transport = Column(String(16), nullable=True)   # 去程交通方式：plane/train/ship/car
    arrive_station = Column(String(64), nullable=True)     # 到达站点：机场/高铁站名
    return_transport = Column(String(16), nullable=True)   # 返程交通方式
    depart_station = Column(String(64), nullable=True)     # 返程出发站点
    ai_version = Column(String(32), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    days = relationship("TripDay", back_populates="trip",
                        order_by="TripDay.day_no", cascade="all, delete-orphan")


class TripDay(Base):
    """按天分组，承载每日主题。"""
    __tablename__ = "trip_days"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    day_no = Column(Integer, nullable=False)
    date = Column(Date, nullable=True)
    theme = Column(String(128), nullable=True)
    city = Column(String(64), nullable=True)  # 当天所在城市（多城市行程逐天标记）

    trip = relationship("Trip", back_populates="days")
