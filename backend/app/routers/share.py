# -*- coding: utf-8 -*-
"""行程分享路由：生成分享链接、只读访问行程。"""
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Trip, TripShare, User
from ..services.seed_planner import compute_day_timeline

router = APIRouter(prefix="/api", tags=["share"])


@router.post("/trips/{trip_id}/share")
def create_share(trip_id: int, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    """生成行程分享链接，7天失效。"""
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == current_user.id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")

    # 生成唯一token
    token = secrets.token_urlsafe(16)
    share = TripShare.create(trip_id=trip_id, token=token, days=7)
    db.add(share)
    db.commit()
    db.refresh(share)

    return {
        "token": token,
        "url": f"/share/{token}",
        "expires_at": share.expires_at.isoformat(),
        "days_valid": 7,
    }


@router.get("/share/{token}")
def get_shared_trip(token: str, db: Session = Depends(get_db)):
    """通过分享token获取行程详情（只读，无需登录）。"""
    share = db.query(TripShare).filter(TripShare.token == token).first()
    if not share:
        raise HTTPException(status_code=404, detail="分享链接不存在")
    if share.is_expired:
        raise HTTPException(status_code=410, detail="分享链接已过期")

    trip = db.query(Trip).filter(Trip.id == share.trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")

    # 构建只读行程数据
    days_data = []
    for day in trip.days:
        days_data.append(compute_day_timeline(db, day))

    return {
        "trip_id": trip.id,
        "title": trip.title,
        "dest_city": trip.dest_city,
        "total_days": trip.total_days,
        "depart_date": trip.depart_date.isoformat() if trip.depart_date else None,
        "return_date": trip.return_date.isoformat() if trip.return_date else None,
        "depart_transport": trip.depart_transport,
        "return_transport": trip.return_transport,
        "arrive_station": trip.arrive_station,
        "depart_station": trip.depart_station,
        "arrive_time": trip.arrive_time.isoformat() if trip.arrive_time else None,
        "depart_time": trip.depart_time.isoformat() if trip.depart_time else None,
        "days": days_data,
        "shared": True,
        "expires_at": share.expires_at.isoformat(),
    }
