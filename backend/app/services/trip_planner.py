# -*- coding: utf-8 -*-
"""行程规划核心服务：天数计算、时间窗口、建行程（含每天记录、多城市分配）。"""
from datetime import date, time, timedelta, datetime

from ..models import Trip, TripDay

# 默认时间假设（M1 采用保守默认，后续可由用户偏好/AI 细化）
AIRPORT_COMMUTE_MIN = 60      # 机场到市区通勤（分钟）
AIRPORT_LEAD_MIN = 180        # 返程起飞前到机场提前量（分钟）
DAY_START = time(8, 0)        # 默认每日游玩开始
DAY_END = time(22, 0)         # 默认每日游玩结束
INTERCITY_MIN = 180           # 城市间切换默认耗时（分钟，第一版固定，将来按城市距离细化）

TRANSPORT_NAMES = {
    "plane": "飞机", "train": "火车", "ship": "轮船", "car": "自驾",
    "taxi": "打车", "bus": "公交", "metro": "地铁", "bike": "自行车", "walk": "步行",
}


def compute_total_days(depart_date: date, return_date: date) -> int:
    """旅行天数 = 返程日期 - 去程日期 + 1。"""
    if return_date < depart_date:
        raise ValueError("返程日期不能早于去程日期")
    return (return_date - depart_date).days + 1


def build_title(dest_cities: list[dict], total_days: int) -> str:
    """标题：大理 4 天 3 晚；多城市：成都+重庆 5 天 4 晚。"""
    cities = [d["city"] for d in dest_cities]
    name = "+".join(cities[:3]) + ("等" if len(cities) > 3 else "")
    nights = total_days - 1
    return f"{name} {total_days} 天 {nights} 晚"


def _add_minutes(t: time, minutes: int) -> time:
    dt = datetime.combine(date(2000, 1, 1), t) + timedelta(minutes=minutes)
    return dt.time()


def _fmt(t: time) -> str:
    return t.strftime("%H:%M")


# 交通方式对应的到达通勤（分钟）和返程提前量（分钟）
TRANSPORT_COMMUTE = {
    "plane": (60, 180, "机场"),
    "train": (30, 60, "车站"),
    "ship": (45, 90, "码头"),
    "car": (0, 0, "自驾"),
}


def compute_day_windows(depart_date: date, arrive_time: time | None,
                        return_date: date, depart_time: time | None,
                        total_days: int,
                        cities: list[str] | None = None,
                        depart_transport: str | None = None,
                        return_transport: str | None = None) -> list[dict]:
    """计算每天的可用游玩时间窗口，供 M2 轨迹图 / M3 AI 求解使用。

    规则：
    - D1：若当日到达（arrive_time 非空），起点 = 到达 + 交通通勤（飞机60/高铁30/客轮45/自驾0）；否则默认 08:00
    - 末日：终点 = 出发 - 交通提前量（飞机180/高铁60/客轮90/自驾0）；若未填出发时间，默认 22:00 结束
    - 中间日：08:00 - 22:00
    - 多城市：当天城市与前一天不同（跨城日），起点顺延城际交通时长（默认 3h）并在 note 标注
    """
    arrive_commute, _, arrive_label = TRANSPORT_COMMUTE.get(depart_transport or "plane", (60, 180, "机场"))
    _, return_lead, return_label = TRANSPORT_COMMUTE.get(return_transport or "plane", (60, 180, "机场"))

    windows = []
    for i in range(1, total_days + 1):
        d = depart_date + timedelta(days=i - 1)
        start, end, note = DAY_START, DAY_END, "全天可安排"

        if i == 1 and arrive_time is not None:
            start = _add_minutes(arrive_time, arrive_commute)
            note = "到达后开始（含%s通勤%d分钟）" % (arrive_label, arrive_commute) if arrive_commute > 0 else "到达后直接开始"
        if i == 1 and arrive_time is None:
            note = "到达时刻未填，默认全天"

        if cities and i > 1 and i <= len(cities) and cities[i - 1] != cities[i - 2]:
            start = _add_minutes(DAY_START, INTERCITY_MIN)
            note = f"由{cities[i - 2]}抵{cities[i - 1]}（城际交通约{INTERCITY_MIN // 60}h）"

        if i == total_days and depart_time is not None:
            end = _add_minutes(depart_time, -return_lead)
            note = "返程前结束（提前%d分钟到%s）" % (return_lead, return_label) if return_lead > 0 else "返程前结束"
        if i == total_days and depart_time is None:
            note = "返程出发时刻未填，默认全天"

        if end <= start:
            # 时间窗异常（如半夜到达），至少给 2h
            end = _add_minutes(start, 120)
            note += "（窗口过短已扩展）"

        windows.append({
            "day_no": i,
            "date": d.isoformat(),
            "start": _fmt(start),
            "end": _fmt(end),
            "note": note,
        })
    return windows


def create_trip_with_days(db, data, user_id: int = None) -> Trip:
    """创建行程主表 + 每天记录（支持多城市 dest_cities）。"""
    total_days = compute_total_days(data.depart_date, data.return_date)

    # 多城市：校验天数之和 = 总天数，按序分配每天城市
    if data.dest_cities:
        cities_plan = [{"city": d.city, "days": d.days} for d in data.dest_cities]
        if sum(d.days for d in data.dest_cities) != total_days:
            raise ValueError(
                f"各城市天数之和（{sum(d.days for d in data.dest_cities)}）须等于旅行总天数（{total_days}）")
        dest_city = cities_plan[0]["city"]
    else:
        cities_plan = [{"city": data.dest_city, "days": total_days}]
        dest_city = data.dest_city

    title = data.title or build_title(cities_plan, total_days)

    trip = Trip(
        user_id=user_id,
        title=title,
        depart_city=data.depart_city,
        dest_city=dest_city,
        depart_date=data.depart_date,
        arrive_time=data.arrive_time,
        return_date=data.return_date,
        depart_time=data.depart_time,
        total_days=total_days,
        status="draft",
        preferences=data.preferences,
        dest_cities=cities_plan,
        depart_transport=getattr(data, 'depart_transport', None),
        arrive_station=getattr(data, 'arrive_station', None),
        return_transport=getattr(data, 'return_transport', None),
        depart_station=getattr(data, 'depart_station', None),
    )
    db.add(trip)
    db.flush()  # 取 trip.id

    # 按城市计划展开每天城市
    day_city = []
    for plan in cities_plan:
        day_city.extend([plan["city"]] * plan["days"])

    for i in range(1, total_days + 1):
        d = data.depart_date + timedelta(days=i - 1)
        db.add(TripDay(trip_id=trip.id, day_no=i, date=d,
                       city=day_city[i - 1] if i - 1 < len(day_city) else dest_city))

    db.commit()
    db.refresh(trip)
    return trip


def duplicate_trip(db, src_trip_id: int, user_id: int = None) -> Trip:
    """深拷贝行程：trip + days + nodes + edges（POI 关联保留，不复制 POI 本身）。"""
    from ..models import TripDay, ItineraryNode, ItineraryEdge

    src = db.get(Trip, src_trip_id)
    if src is None:
        raise ValueError("行程不存在")

    # 1. 复制 trip 主记录
    new_trip = Trip(
        user_id=user_id,
        title=(src.title or "") + " 副本",
        depart_city=src.depart_city,
        dest_city=src.dest_city,
        depart_date=src.depart_date,
        arrive_time=src.arrive_time,
        return_date=src.return_date,
        depart_time=src.depart_time,
        total_days=src.total_days,
        status="draft",
        preferences=src.preferences,
        dest_cities=src.dest_cities,
        ai_version=src.ai_version,
    )
    db.add(new_trip)
    db.flush()

    # 2. 复制 days，建立 old_day_id → new_day_id
    day_map = {}
    for d in src.days:
        nd = TripDay(trip_id=new_trip.id, day_no=d.day_no, date=d.date,
                     theme=d.theme, city=d.city)
        db.add(nd)
        db.flush()
        day_map[d.id] = nd.id

    # 3. 复制 nodes，建立 old_node_id → new_node_id
    src_nodes = db.query(ItineraryNode).filter(ItineraryNode.trip_id == src_trip_id).all()
    node_map = {}
    for n in src_nodes:
        nn = ItineraryNode(
            trip_id=new_trip.id,
            day_id=day_map.get(n.day_id),
            poi_id=n.poi_id,
            node_type=n.node_type,
            name=n.name,
            start_time=n.start_time,
            duration_minutes=n.duration_minutes,
            sort_order=n.sort_order,
            note=n.note,
            lat=n.lat,
            lng=n.lng,
            locked=n.locked,
        )
        db.add(nn)
        db.flush()
        node_map[n.id] = nn.id

    # 4. 复制 edges，from/to 用新 id
    src_edges = db.query(ItineraryEdge).filter(ItineraryEdge.trip_id == src_trip_id).all()
    for e in src_edges:
        if e.from_node_id in node_map and e.to_node_id in node_map:
            db.add(ItineraryEdge(
                trip_id=new_trip.id,
                from_node_id=node_map[e.from_node_id],
                to_node_id=node_map[e.to_node_id],
                transport=e.transport,
                duration_minutes=e.duration_minutes,
                note=e.note,
            ))

    db.commit()
    db.refresh(new_trip)
    return new_trip
