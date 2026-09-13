# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Trip, User, ItineraryNode
from ..schemas import TripCreate, TripOut, TripCreateOut, DayWindowOut
from ..services import trip_planner

router = APIRouter(prefix="/api/trips", tags=["trips"])

# 行程状态机：draft(草稿) -> planning(规划中) -> active(进行中) -> finalized(已定稿)
VALID_STATUSES = {"draft", "planning", "active", "done", "finalized"}


def _own_trip(db: Session, trip_id: int, user: User) -> Trip:
    """获取并校验行程归属。"""
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")
    if trip.user_id is not None and trip.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该行程")
    return trip


@router.post("", response_model=TripCreateOut, status_code=201)
def create_trip(data: TripCreate, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    """创建行程：航班输入 → 自动算天数 → 生成每天记录与时间窗口。"""
    try:
        trip = trip_planner.create_trip_with_days(db, data, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    windows = trip_planner.compute_day_windows(
        trip.depart_date, trip.arrive_time,
        trip.return_date, trip.depart_time,
        trip.total_days,
        cities=[d.city or trip.dest_city for d in trip.days],
        depart_transport=trip.depart_transport,
        return_transport=trip.return_transport,
    )
    messages = []
    transport_names = {'plane': '航班', 'train': '高铁', 'car': '自驾', 'ship': '客轮'}
    depart_name = transport_names.get(trip.depart_transport, '交通')
    return_name = transport_names.get(trip.return_transport, '交通')
    if trip.arrive_time is None:
        messages.append(f"去程到达时刻未填，D1 按全天计算，建议补充{depart_name}信息")
    if trip.depart_time is None:
        messages.append(f"返程出发时刻未填，末日按全天计算，建议补充{return_name}信息")

    return TripCreateOut(trip=TripOut.model_validate(trip),
                         windows=[DayWindowOut(**w) for w in windows],
                         messages=messages)


@router.get("", response_model=list[TripOut])
def list_trips(db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    """当前用户的行程列表，按创建时间倒序。"""
    return (db.query(Trip)
            .filter(Trip.user_id == current_user.id)
            .order_by(Trip.created_at.desc()).all())


@router.get("/{trip_id}", response_model=TripOut)
def get_trip(trip_id: int, db: Session = Depends(get_db),
             current_user: User = Depends(get_current_user)):
    return _own_trip(db, trip_id, current_user)


@router.delete("/{trip_id}", status_code=204)
def delete_trip(trip_id: int, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    trip = _own_trip(db, trip_id, current_user)
    db.delete(trip)
    db.commit()


@router.patch("/{trip_id}", response_model=TripOut)
def update_trip(trip_id: int, payload: dict, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    """轻量更新：title / status / preferences 等。"""
    trip = _own_trip(db, trip_id, current_user)
    allowed = {"title", "status", "preferences", "ai_version"}
    for k, v in payload.items():
        if k in allowed:
            if k == "status" and v not in VALID_STATUSES:
                raise HTTPException(status_code=422, detail=f"无效的状态值: {v}")
            setattr(trip, k, v)
    db.commit()
    db.refresh(trip)
    return trip


@router.post("/{trip_id}/finalize", response_model=TripOut)
def finalize_trip(trip_id: int, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    """行程定稿：行程节点已生成且无冲突后，将行程置为 finalized，供下游（TripMemory）同步。

    定稿条件：
    1. 行程至少包含一个节点；
    2. 时间线无冲突（如有冲突需先解决）。
    """
    trip = _own_trip(db, trip_id, current_user)
    node_count = (db.query(ItineraryNode)
                  .filter(ItineraryNode.trip_id == trip_id).count())
    if node_count == 0:
        raise HTTPException(status_code=422, detail="行程还没有任何节点，无法定稿，请先 AI 生成或手动添加")

    # 时间线冲突检查（复用时间线计算逻辑）
    from ..services.seed_planner import compute_day_timeline
    conflicts = []
    for day in trip.days:
        tl = compute_day_timeline(db, day)
        if tl.get("conflict"):
            overflow = tl.get("overflow_min", 0)
            conflicts.append(f"第{day.day_no}天：行程超出可用时间{overflow}分钟，请调整节点时长或交通方式")
    if conflicts:
        raise HTTPException(status_code=422, detail="行程时间线存在冲突，无法定稿：" + "；".join(conflicts[:3]))

    trip.status = "finalized"
    db.commit()
    db.refresh(trip)
    return trip


@router.post("/{trip_id}/unfinalize", response_model=TripOut)
def unfinalize_trip(trip_id: int, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    """取消定稿：回到草稿状态，可继续编辑。"""
    trip = _own_trip(db, trip_id, current_user)
    trip.status = "draft"
    db.commit()
    db.refresh(trip)
    return trip


@router.post("/{trip_id}/duplicate", response_model=TripOut, status_code=201)
def duplicate_trip(trip_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    """深拷贝行程（含每天、节点、交通边；POI 关联保留）。"""
    _own_trip(db, trip_id, current_user)
    try:
        return trip_planner.duplicate_trip(db, trip_id, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
