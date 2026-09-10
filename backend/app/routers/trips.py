# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Trip
from ..schemas import TripCreate, TripOut, TripCreateOut, DayWindowOut
from ..services import trip_planner

router = APIRouter(prefix="/api/trips", tags=["trips"])


@router.post("", response_model=TripCreateOut, status_code=201)
def create_trip(data: TripCreate, db: Session = Depends(get_db)):
    """创建行程：航班输入 → 自动算天数 → 生成每天记录与时间窗口。"""
    try:
        trip = trip_planner.create_trip_with_days(db, data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    windows = trip_planner.compute_day_windows(
        trip.depart_date, trip.arrive_time,
        trip.return_date, trip.depart_time,
        trip.total_days,
        cities=[d.city or trip.dest_city for d in trip.days],
    )
    messages = []
    if trip.arrive_time is None:
        messages.append("去程到达时刻未填，D1 按全天计算，建议补充航班信息")
    if trip.depart_time is None:
        messages.append("返程起飞时刻未填，末日按全天计算，建议补充航班信息")

    return TripCreateOut(trip=TripOut.model_validate(trip),
                         windows=[DayWindowOut(**w) for w in windows],
                         messages=messages)


@router.get("", response_model=list[TripOut])
def list_trips(db: Session = Depends(get_db)):
    """行程列表，按创建时间倒序。"""
    return db.query(Trip).order_by(Trip.created_at.desc()).all()


@router.get("/{trip_id}", response_model=TripOut)
def get_trip(trip_id: int, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")
    return trip


@router.delete("/{trip_id}", status_code=204)
def delete_trip(trip_id: int, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")
    db.delete(trip)
    db.commit()


@router.patch("/{trip_id}", response_model=TripOut)
def update_trip(trip_id: int, payload: dict, db: Session = Depends(get_db)):
    """轻量更新：title / status / preferences 等。"""
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")
    allowed = {"title", "status", "preferences", "ai_version"}
    for k, v in payload.items():
        if k in allowed:
            setattr(trip, k, v)
    db.commit()
    db.refresh(trip)
    return trip


@router.post("/{trip_id}/duplicate", response_model=TripOut, status_code=201)
def duplicate_trip(trip_id: int, db: Session = Depends(get_db)):
    """深拷贝行程（含每天、节点、交通边；POI 关联保留）。"""
    try:
        return trip_planner.duplicate_trip(db, trip_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
