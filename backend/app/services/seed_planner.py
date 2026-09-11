# -*- coding: utf-8 -*-
"""轨迹图核心服务：种子骨架生成、时间线计算、顺序调整与边重建。"""
import random
from datetime import date, time, timedelta, datetime

from sqlalchemy.orm import Session

from ..models import Trip, TripDay, ItineraryNode, ItineraryEdge
from .trip_planner import compute_day_windows
from .poi_service import search_pois
from . import distance_service

# 交通模式默认耗时（分钟），切换交通时按此值重算；用户可再微调
TRANSPORT_DEFAULTS = {
    "walk": 15,
    "bike": 20,
    "bus": 30,
    "metro": 35,
    "taxi": 25,
    "car": 30,
    "train": 60,
    "ship": 45,
    "plane": 120,
}

TRANSPORT_NAMES = {
    "plane": "飞机", "train": "火车", "ship": "轮船", "car": "自驾",
    "taxi": "打车", "bus": "公交", "metro": "地铁", "bike": "自行车", "walk": "步行",
}

HOTEL_MORNING_MIN = 30   # 酒店：早餐/出发准备
HOTEL_EVENING_MIN = 30   # 酒店：回程入住/休整
ATTRACTION_MIN = 180     # 景点
RESTAURANT_MIN = 90      # 餐厅


def _add_minutes(t: time, minutes: int) -> time:
    return (datetime.combine(date(2000, 1, 1), t) + timedelta(minutes=minutes)).time()


def _min_diff(start: time, end: time) -> int:
    s = datetime.combine(date(2000, 1, 1), start)
    e = datetime.combine(date(2000, 1, 1), end)
    return int((e - s).total_seconds() // 60)


def _fmt(t: time) -> str:
    return t.strftime("%H:%M")


def _build_day_template(day_no: int, total_days: int, dest_city: str,
                        window_start: time, window_end: time) -> list[dict]:
    """按天类型生成骨架节点模板（不含边）。

    - 首日：酒店 → 景点A → 餐厅A → 酒店
    - 末日：酒店 → 景点A → 餐厅A → 酒店（窗口短时裁剪）
    - 中间日：酒店 → 景点A → 餐厅A → 景点B → 餐厅B → 酒店
    """
    hotel = {"node_type": "hotel", "name": f"{dest_city} 酒店", "duration_minutes": HOTEL_MORNING_MIN}
    hotel_eve = {"node_type": "hotel", "name": f"{dest_city} 酒店", "duration_minutes": HOTEL_EVENING_MIN}
    a1 = {"node_type": "attraction", "name": "本地景点 A", "duration_minutes": ATTRACTION_MIN}
    a2 = {"node_type": "attraction", "name": "本地景点 B", "duration_minutes": ATTRACTION_MIN}
    r1 = {"node_type": "restaurant", "name": "特色餐厅 A", "duration_minutes": RESTAURANT_MIN}
    r2 = {"node_type": "restaurant", "name": "特色餐厅 B", "duration_minutes": RESTAURANT_MIN}

    is_first = day_no == 1
    is_last = day_no == total_days

    if is_first:
        base = [hotel, a1, r1, hotel_eve]
    elif is_last:
        base = [hotel, a1, r1, hotel_eve]
    else:
        base = [hotel, a1, r1, a2, r2, hotel_eve]

    # 窗口过短时裁剪尾部（先保景点与餐厅，最后保留的收尾酒店可去掉）
    window_min = _min_diff(window_start, window_end)
    fixed_edges = (len(base) - 1) * TRANSPORT_DEFAULTS["walk"]
    while len(base) > 2:
        total = sum(n["duration_minutes"] for n in base) + fixed_edges
        if total <= window_min:
            break
        base.pop(-2)  # 去掉倒数第二个（餐厅或景点）
    return base


def seed_trip_timeline(db: Session, trip: Trip) -> bool:
    """为行程生成默认骨架（幂等：已有节点则跳过）。返回是否本次生成。"""
    if db.query(ItineraryNode).filter(ItineraryNode.trip_id == trip.id).first():
        return False

    windows = compute_day_windows(trip.depart_date, trip.arrive_time,
                                  trip.return_date, trip.depart_time, trip.total_days,
                                  cities=_trip_day_cities(db, trip))
    days = db.query(TripDay).filter(TripDay.trip_id == trip.id).order_by(TripDay.day_no).all()
    day_by_no = {d.day_no: d for d in days}

    for w in windows:
        day = day_by_no.get(w["day_no"])
        if not day:
            continue
        day_city = day.city or trip.dest_city
        ws = time.fromisoformat(w["start"])
        we = time.fromisoformat(w["end"])
        template = _build_day_template(w["day_no"], trip.total_days, day_city, ws, we)

        order = 0
        nodes = []
        for item in template:
            order += 1
            # 约 70% 节点关联该天所属城市同类型真实 POI，其余保留占位（统称，待细化）
            poi = None
            name = item["name"]
            if random.random() < 0.7:
                cands = search_pois(db, city=day_city, poi_type=item["node_type"], limit=20)
                if cands:
                    poi = random.choice(cands)
                    name = poi.name
            node = ItineraryNode(
                trip_id=trip.id, day_id=day.id, node_type=item["node_type"],
                name=name, duration_minutes=item["duration_minutes"],
                sort_order=order, poi_id=poi.id if poi else None,
            )
            db.add(node)
            nodes.append(node)
        db.flush()

        # 相邻节点之间生成边，按距离自动选择交通方式
        for k in range(len(nodes) - 1):
            t = distance_service.calc_transport(db, nodes[k], nodes[k + 1])
            db.add(ItineraryEdge(
                trip_id=trip.id,
                from_node_id=nodes[k].id,
                to_node_id=nodes[k + 1].id,
                transport=t["transport"],
                duration_minutes=t["duration_minutes"],
                distance_km=t["distance_km"],
            ))

    db.commit()
    return True


def _rebuild_day_edges(db: Session, trip_id: int, day_id: int, nodes: list[ItineraryNode]) -> None:
    """按节点新顺序重建当天边：相邻对尽量复用旧边交通信息，否则默认步行。"""
    day_node_ids = {n.id for n in nodes}

    # 收集当天旧边
    old = (db.query(ItineraryEdge)
           .filter(ItineraryEdge.trip_id == trip_id,
                   ItineraryEdge.from_node_id.in_(day_node_ids))
           .all())
    old_by_pair = {}
    for e in old:
        key = frozenset((e.from_node_id, e.to_node_id))
        old_by_pair[key] = e

    # 删除当天旧边（不触碰其他天的边）
    (db.query(ItineraryEdge)
     .filter(ItineraryEdge.trip_id == trip_id,
             ItineraryEdge.from_node_id.in_(day_node_ids))
     .delete(synchronize_session=False))

    for k in range(len(nodes) - 1):
        a, b = nodes[k], nodes[k + 1]
        pair = frozenset((a.id, b.id))
        prev = old_by_pair.get(pair)
        if prev is not None:
            # 复用旧边的交通方式，但重新计算距离和时间
            t = distance_service.calc_transport(db, a, b)
            transport = prev.transport
            dur = prev.duration_minutes
            dist = t["distance_km"]
        else:
            t = distance_service.calc_transport(db, a, b)
            transport, dur, dist = t["transport"], t["duration_minutes"], t["distance_km"]
        db.add(ItineraryEdge(
            trip_id=trip_id,
            from_node_id=a.id,
            to_node_id=b.id,
            transport=transport,
            duration_minutes=dur,
            distance_km=dist,
        ))


def _trip_day_cities(db: Session, trip: Trip) -> list[str]:
    """行程每天城市列表（按 day_no，回退 dest_city）。"""
    days = (db.query(TripDay)
            .filter(TripDay.trip_id == trip.id)
            .order_by(TripDay.day_no)
            .all())
    return [d.city or trip.dest_city for d in days]


def compute_day_timeline(db: Session, day: TripDay) -> dict:
    """计算某天时间线：每段起止时间、总占用、冲突检测。"""
    trip = db.get(Trip, day.trip_id)
    windows = compute_day_windows(trip.depart_date, trip.arrive_time,
                                  trip.return_date, trip.depart_time, trip.total_days,
                                  cities=_trip_day_cities(db, trip))
    w = next((x for x in windows if x["day_no"] == day.day_no), None)
    if not w:
        return {"day_no": day.day_no, "date": day.date.isoformat(),
                "window_start": "", "window_end": "", "note": "",
                "total_used_min": 0, "conflict": False, "overflow_min": 0,
                "nodes": [], "edges": []}

    ws = time.fromisoformat(w["start"])
    we = time.fromisoformat(w["end"])

    nodes = (db.query(ItineraryNode)
             .filter(ItineraryNode.day_id == day.id)
             .order_by(ItineraryNode.sort_order, ItineraryNode.id)
             .all())
    node_ids = [n.id for n in nodes]
    edges = (db.query(ItineraryEdge)
             .filter(ItineraryEdge.trip_id == day.trip_id,
                     ItineraryEdge.from_node_id.in_(node_ids))
             .all())
    edge_by_from = {e.from_node_id: e for e in edges}

    # POI 摘要映射（真实地点特有数据：营业时间/票价/地址）
    poi_by_id = {}
    poi_ids = {n.poi_id for n in nodes if n.poi_id}
    if poi_ids:
        from ..models import Poi
        for p in db.query(Poi).filter(Poi.id.in_(poi_ids)).all():
            poi_by_id[p.id] = p

    cursor = ws
    node_outs = []
    used = 0
    for i, node in enumerate(nodes):
        start = cursor
        end = _add_minutes(start, node.duration_minutes)
        used += node.duration_minutes
        poi = poi_by_id.get(node.poi_id) if node.poi_id else None
        node_outs.append({
            "id": node.id,
            "node_type": node.node_type,
            "name": node.name,
            "duration_minutes": node.duration_minutes,
            "sort_order": node.sort_order,
            "note": node.note,
            "poi_id": node.poi_id,
            "poi": {
                "id": poi.id, "city": poi.city, "poi_type": poi.poi_type,
                "name": poi.name, "address": poi.address,
                "open_hours": poi.open_hours, "ticket_price": poi.ticket_price,
                "rating": float(poi.rating) if poi.rating is not None else None,
                "source": poi.source,
            } if poi else None,
            "start_time": _fmt(start),
            "end_time": _fmt(end),
        })
        cursor = end
        if i < len(nodes) - 1:
            edge = edge_by_from.get(node.id)
            dur = edge.duration_minutes if edge else TRANSPORT_DEFAULTS["walk"]
            used += dur
            cursor = _add_minutes(cursor, dur)

    edge_outs = []
    for e in edges:
        edge_outs.append({
            "id": e.id,
            "from_node_id": e.from_node_id,
            "to_node_id": e.to_node_id,
            "transport": e.transport,
            "duration_minutes": e.duration_minutes,
            "distance_km": float(e.distance_km) if e.distance_km else None,
            "note": e.note,
        })

    window_min = _min_diff(ws, we)
    overflow = max(0, used - window_min)
    return {
        "day_no": day.day_no,
        "date": day.date.isoformat(),
        "city": day.city or trip.dest_city,
        "window_start": w["start"],
        "window_end": w["end"],
        "note": w["note"],
        "total_used_min": used,
        "conflict": overflow > 0,
        "overflow_min": overflow,
        "nodes": node_outs,
        "edges": edge_outs,
    }


def move_node(db: Session, node: ItineraryNode, direction: str) -> None:
    """节点在同一天内上移/下移，并重建当天边。"""
    if direction not in ("up", "down"):
        raise ValueError("direction 仅支持 up/down")

    siblings = (db.query(ItineraryNode)
                .filter(ItineraryNode.day_id == node.day_id)
                .order_by(ItineraryNode.sort_order, ItineraryNode.id)
                .all())
    idx = siblings.index(node)
    target = idx - 1 if direction == "up" else idx + 1
    if target < 0 or target >= len(siblings):
        raise ValueError("已在边界，无法移动")

    siblings[idx], siblings[target] = siblings[target], siblings[idx]
    for i, n in enumerate(siblings, start=1):
        n.sort_order = i

    _rebuild_day_edges(db, node.trip_id, node.day_id, siblings)
    db.commit()
