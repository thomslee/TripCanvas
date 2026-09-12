# -*- coding: utf-8 -*-
"""行程分享链接模型。"""
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class TripShare(Base):
    """行程分享链接：生成只读分享链接，7天失效。"""
    __tablename__ = "trip_shares"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)  # 7天后失效

    trip = relationship("Trip", back_populates="shares")

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    @classmethod
    def create(cls, trip_id: int, token: str, days: int = 7) -> "TripShare":
        return cls(
            trip_id=trip_id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(days=days),
        )
