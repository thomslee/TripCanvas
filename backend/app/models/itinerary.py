# -*- coding: utf-8 -*-
from datetime import datetime
from sqlalchemy import Column, Integer, String, Time, Boolean, DateTime, ForeignKey, DECIMAL
from ..database import Base


class ItineraryNode(Base):
    """轨迹图顶点：节点与占用时间。"""
    __tablename__ = "itinerary_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    day_id = Column(Integer, ForeignKey("trip_days.id", ondelete="CASCADE"), nullable=True)
    city = Column(String(64), nullable=True)  # 节点所在城市（跨城天可能与day.city不同）
    poi_id = Column(Integer, ForeignKey("pois.id", ondelete="SET NULL"), nullable=True)  # 关联真实地点
    node_type = Column(String(16), nullable=False)  # hotel/attraction/restaurant/transfer
    name = Column(String(128), nullable=False)
    start_time = Column(Time, nullable=True)
    duration_minutes = Column(Integer, nullable=False, default=60)
    sort_order = Column(Integer, nullable=False, default=0)
    note = Column(String(255), nullable=True)
    lat = Column(DECIMAL(10, 7), nullable=True)
    lng = Column(DECIMAL(10, 7), nullable=True)
    locked = Column(Boolean, nullable=False, default=False)  # 二次推荐锁定
    created_at = Column(DateTime, default=datetime.now)


class ItineraryEdge(Base):
    """轨迹图边：交通工具与耗时。"""
    __tablename__ = "itinerary_edges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    from_node_id = Column(Integer, ForeignKey("itinerary_nodes.id", ondelete="CASCADE"), nullable=False)
    to_node_id = Column(Integer, ForeignKey("itinerary_nodes.id", ondelete="CASCADE"), nullable=False)
    transport = Column(String(16), nullable=False)  # plane/train/ship/car/taxi/bus/metro/bike/walk
    duration_minutes = Column(Integer, nullable=False, default=30)
    distance_km = Column(DECIMAL(6, 2), nullable=True)  # 两点间距离（公里）
    note = Column(String(255), nullable=True)
