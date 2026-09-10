# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Trip, TripDay, ItineraryNode, ItineraryEdge, Poi
from ..schemas.itinerary import (
    NodeCreate, NodeOut, NodePatch, EdgeOut, EdgePatch,
    DayTimelineOut, TimelineOut, MovePayload, ReorderPayload, TripPoiOut, PoiSummary,
)
from ..services import seed_planner, replan_service

router = APIRouter(prefix="/api", tags=["itinerary"])

_TYPE_NAMES = {"hotel": "酒店", "attraction": "景点", "restaurant": "餐厅"}


def _get_trip(db: Session, trip_id: int) -> Trip:
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")
    return trip


def _get_day(db: Session, trip_id: int, day_no: int) -> TripDay:
    day = (db.query(TripDay)
           .filter(TripDay.trip_id == trip_id, TripDay.day_no == day_no)
           .first())
    if not day:
        raise HTTPException(status_code=404, detail="该天不存在")
    return day


def _get_node(db: Session, node_id: int) -> ItineraryNode:
    node = db.get(ItineraryNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")
    return node


def _resolve_poi(db: Session, poi_id: int | None) -> Poi | None:
    if not poi_id:
        return None
    poi = db.get(Poi, poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="POI 不存在")
    return poi


def _node_out(node: ItineraryNode, poi: Poi | None) -> NodeOut:
    out = NodeOut.model_validate(node)
    if poi:
        out.poi = PoiSummary.model_validate(poi)
    return out


@router.post("/trips/{trip_id}/seed", status_code=200)
def seed_trip(trip_id: int, db: Session = Depends(get_db)):
    """为行程生成默认骨架（已有节点则跳过）。"""
    trip = _get_trip(db, trip_id)
    created = seed_planner.seed_trip_timeline(db, trip)
    return {"seeded": created, "message": "已生成默认骨架" if created else "已有内容，跳过生成"}


@router.get("/trips/{trip_id}/timeline", response_model=TimelineOut)
def get_timeline(trip_id: int, db: Session = Depends(get_db)):
    """行程轨迹时间线：每天窗口 + 节点起止时间 + 交通边 + 冲突检测。"""
    trip = _get_trip(db, trip_id)
    days = (db.query(TripDay)
            .filter(TripDay.trip_id == trip_id)
            .order_by(TripDay.day_no)
            .all())
    return TimelineOut(
        trip_id=trip.id,
        title=trip.title,
        dest_city=trip.dest_city,
        dest_cities=trip.dest_cities,
        days=[DayTimelineOut(**seed_planner.compute_day_timeline(db, d)) for d in days],
    )


@router.get("/trips/{trip_id}/pois", response_model=list[TripPoiOut])
def list_trip_pois(trip_id: int, db: Session = Depends(get_db)):
    """行程中使用的真实地点清单（去重），供侧边列表展示与删除联动。"""
    _get_trip(db, trip_id)
    rows = (db.query(ItineraryNode.poi_id, func.count(ItineraryNode.id))
            .filter(ItineraryNode.trip_id == trip_id,
                    ItineraryNode.poi_id.isnot(None))
            .group_by(ItineraryNode.poi_id)
            .order_by(func.count(ItineraryNode.id).desc())
            .all())
    result = []
    for poi_id, cnt in rows:
        poi = db.get(Poi, poi_id)
        if not poi:
            continue
        node_ids = [n.id for n in
                    db.query(ItineraryNode)
                    .filter(ItineraryNode.trip_id == trip_id,
                            ItineraryNode.poi_id == poi_id)
                    .all()]
        result.append(TripPoiOut(poi=PoiSummary.model_validate(poi),
                                 count=cnt, node_ids=node_ids))
    return result


@router.delete("/trips/{trip_id}/pois/{poi_id}", status_code=204)
def delete_trip_poi(trip_id: int, poi_id: int, db: Session = Depends(get_db)):
    """从行程删除该真实地点：轨迹图中关联节点一并删除，边自动重建。"""
    _get_trip(db, trip_id)
    nodes = (db.query(ItineraryNode)
             .filter(ItineraryNode.trip_id == trip_id,
                     ItineraryNode.poi_id == poi_id)
             .all())
    if not nodes:
        raise HTTPException(status_code=404, detail="该地点不在行程中")

    day_ids = {n.day_id for n in nodes}
    for n in nodes:
        db.delete(n)
    db.flush()

    for day_id in day_ids:
        siblings = (db.query(ItineraryNode)
                    .filter(ItineraryNode.day_id == day_id)
                    .order_by(ItineraryNode.sort_order, ItineraryNode.id)
                    .all())
        for i, n in enumerate(siblings, start=1):
            n.sort_order = i
        seed_planner._rebuild_day_edges(db, trip_id, day_id, siblings)
    db.commit()


@router.post("/trips/{trip_id}/days/{day_no}/nodes", response_model=NodeOut, status_code=201)
def add_node(trip_id: int, day_no: int, data: NodeCreate, db: Session = Depends(get_db)):
    """新增节点：支持关联真实 POI 与插入到指定节点之后。"""
    _get_trip(db, trip_id)
    day = _get_day(db, trip_id, day_no)
    poi = _resolve_poi(db, data.poi_id)

    name = data.name
    if poi:
        name = poi.name

    # 插入位置：after_node_id>0 指定节点之后；=-1 插入最前面；缺省追加末尾
    if data.after_node_id and data.after_node_id > 0:
        after = _get_node(db, data.after_node_id)
        if after.day_id != day.id:
            raise HTTPException(status_code=400, detail="after_node_id 不属于当天")
        (db.query(ItineraryNode)
         .filter(ItineraryNode.day_id == day.id,
                 ItineraryNode.sort_order > after.sort_order)
         .update({ItineraryNode.sort_order: ItineraryNode.sort_order + 1},
                 synchronize_session=False))
        order = after.sort_order + 1
    elif data.after_node_id == -1:
        (db.query(ItineraryNode)
         .filter(ItineraryNode.day_id == day.id)
         .update({ItineraryNode.sort_order: ItineraryNode.sort_order + 1},
                 synchronize_session=False))
        order = 1
    else:
        max_order = (db.query(ItineraryNode)
                     .filter(ItineraryNode.day_id == day.id)
                     .order_by(ItineraryNode.sort_order.desc())
                     .first())
        order = (max_order.sort_order + 1 if max_order else 1)

    node = ItineraryNode(
        trip_id=trip_id, day_id=day.id,
        node_type=data.node_type, name=name,
        duration_minutes=data.duration_minutes,
        sort_order=order, note=data.note,
        poi_id=poi.id if poi else None,
    )
    db.add(node)
    db.flush()

    siblings = (db.query(ItineraryNode)
                .filter(ItineraryNode.day_id == day.id)
                .order_by(ItineraryNode.sort_order, ItineraryNode.id)
                .all())
    seed_planner._rebuild_day_edges(db, trip_id, day.id, siblings)
    db.commit()
    db.refresh(node)
    return _node_out(node, poi)


@router.patch("/nodes/{node_id}", response_model=NodeOut)
def patch_node(node_id: int, data: NodePatch, db: Session = Depends(get_db)):
    """修改节点：名称 / 类型 / 时长 / 备注 / 关联真实 POI（poi_id=0 清除）。"""
    node = _get_node(db, node_id)
    patch = data.model_dump(exclude_unset=True)

    poi = None
    if "poi_id" in patch:
        if patch["poi_id"]:
            poi = _resolve_poi(db, patch["poi_id"])
            node.poi_id = poi.id
            node.name = poi.name  # 选定真实地点后名称以 POI 为准
            node.node_type = poi.poi_type
        else:
            node.poi_id = None
            node.name = f"{_TYPE_NAMES.get(node.node_type, node.node_type)}（占位）"  # 清除关联，恢复占位
        patch.pop("poi_id")

    for k, v in patch.items():
        if v is not None:
            setattr(node, k, v)
    db.commit()
    db.refresh(node)
    if node.poi_id and poi is None:
        poi = db.get(Poi, node.poi_id)
    return _node_out(node, poi)


@router.delete("/nodes/{node_id}", status_code=204)
def delete_node(node_id: int, db: Session = Depends(get_db)):
    """删除节点并重建当天边。"""
    node = _get_node(db, node_id)
    trip_id, day_id = node.trip_id, node.day_id
    db.delete(node)
    db.flush()
    siblings = (db.query(ItineraryNode)
                .filter(ItineraryNode.day_id == day_id)
                .order_by(ItineraryNode.sort_order, ItineraryNode.id)
                .all())
    for i, n in enumerate(siblings, start=1):
        n.sort_order = i
    seed_planner._rebuild_day_edges(db, trip_id, day_id, siblings)
    db.commit()


@router.post("/nodes/{node_id}/move", status_code=200)
def move_node(node_id: int, payload: MovePayload, db: Session = Depends(get_db)):
    """节点当天内上移/下移（顺序交换后重建边）。"""
    node = _get_node(db, node_id)
    try:
        seed_planner.move_node(db, node, payload.direction)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "direction": payload.direction}


@router.patch("/edges/{edge_id}", response_model=EdgeOut)
def patch_edge(edge_id: int, data: EdgePatch, db: Session = Depends(get_db)):
    """切换交通方式（未给耗时则按默认值重算）或微调耗时。"""
    edge = db.get(ItineraryEdge, edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail="边不存在")

    patch = data.model_dump(exclude_unset=True)
    if "transport" in patch and patch["transport"]:
        edge.transport = patch["transport"]
        if "duration_minutes" not in patch:
            edge.duration_minutes = seed_planner.TRANSPORT_DEFAULTS.get(
                edge.transport, 30)
    if "duration_minutes" in patch and patch["duration_minutes"]:
        edge.duration_minutes = patch["duration_minutes"]
    if "note" in patch:
        edge.note = patch["note"]
    db.commit()
    db.refresh(edge)
    return edge


@router.post("/trips/{trip_id}/days/{day_no}/reorder", status_code=200)
def reorder_day(trip_id: int, day_no: int, payload: ReorderPayload,
                db: Session = Depends(get_db)):
    """按节点 id 列表重排当天顺序（拖拽/批量排序提交），并重建边。"""
    _get_trip(db, trip_id)
    day = _get_day(db, trip_id, day_no)
    order_map = {nid: i for i, nid in enumerate(payload.node_ids, start=1)}
    if len(order_map) != len(payload.node_ids):
        raise HTTPException(status_code=400, detail="node_ids 存在重复")

    nodes = (db.query(ItineraryNode)
             .filter(ItineraryNode.day_id == day.id)
             .all())
    if len(nodes) != len(payload.node_ids):
        raise HTTPException(status_code=400, detail="节点数量与请求不一致")
    id_set = {n.id for n in nodes}
    if not set(payload.node_ids).issubset(id_set):
        raise HTTPException(status_code=400, detail="包含不属于当天的节点")

    for n in nodes:
        n.sort_order = order_map[n.id]
    ordered = sorted(nodes, key=lambda n: n.sort_order)
    seed_planner._rebuild_day_edges(db, trip_id, day.id, ordered)
    db.commit()
    return {"ok": True, "count": len(ordered)}


@router.post("/trips/{trip_id}/replan", status_code=200)
def replan_trip(trip_id: int, db: Session = Depends(get_db)):
    """AI 二次推荐：按评分 / 类型分布 / 营业时间对现有节点智能重排（不增删节点）。"""
    trip = _get_trip(db, trip_id)
    result = replan_service.replan_trip(db, trip)
    timeline = get_timeline(trip_id, db)
    return {**result, "timeline": timeline}
