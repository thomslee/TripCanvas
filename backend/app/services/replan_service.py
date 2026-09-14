# -*- coding: utf-8 -*-
"""AI 二次推荐：基于用户确定的地点，调用大模型重新规划整个行程。
保留用户手动增删的地点集合，AI重新安排顺序和时间，确保往返时间合理。"""
import re
import json
import datetime as dt
from typing import Optional

from sqlalchemy.orm import Session

from ..models import Trip, TripDay, ItineraryNode, ItineraryEdge, Poi, User
from . import seed_planner, ai_planner, llm_service


def _rating(node: ItineraryNode) -> float:
    return float(node.poi.rating) if node.poi and node.poi.rating else 0.0


def _open_window(poi: Optional[dict]) -> Optional[tuple[dt.time, dt.time]]:
    """解析营业时间 '07:30-18:30'（兼容 '24小时/全天开放'，含闭馆备注）。poi 为 timeline 节点携带的 dict。"""
    if not poi or not poi.get("open_hours"):
        return None
    s = poi["open_hours"]
    m = re.search(r"(\d{1,2}:\d{2})\s*[-~]\s*(\d{1,2}:\d{2})", s)
    if not m:
        return None
    try:
        return dt.time.fromisoformat(m.group(1)), dt.time.fromisoformat(m.group(2))
    except ValueError:
        return None


def _interleave(items: list) -> list:
    """类型交替微调：连续 >=3 个同类型时，将后续与之后最近的不同类型交换（一遍贪心）。"""
    out = list(items)
    n = len(out)
    i = 0
    while i < n - 2:
        a, b, c = out[i], out[i + 1], out[i + 2]
        if a.node_type == b.node_type == c.node_type and a.node_type != "hotel":
            # 找之后第一个不同类型
            j = i + 3
            while j < n and out[j].node_type == a.node_type:
                j += 1
            if j < n:
                out[i + 2], out[j] = out[j], out[i + 2]
                i += 2  # 交换后从 i+2 继续检查
                continue
        i += 1
    return out


def _apply_order(db: Session, day: TripDay, ordered: list[ItineraryNode]) -> None:
    for idx, node in enumerate(ordered, start=1):
        node.sort_order = idx
    seed_planner._rebuild_day_edges(db, day.trip_id, day.id, ordered)
    db.flush()


def _rebuild_from_db(db: Session, day: TripDay) -> None:
    """按数据库当前 sort_order 顺序重建当天边（交换节点后使用）。"""
    ordered = (db.query(ItineraryNode)
               .filter(ItineraryNode.day_id == day.id)
               .order_by(ItineraryNode.sort_order)
               .all())
    seed_planner._rebuild_day_edges(db, day.trip_id, day.id, ordered)
    db.flush()


def _fmt_mm(t: Optional[dt.time]) -> int:
    return t.hour * 60 + t.minute if t else 0


def replan_trip(db: Session, trip: Trip) -> dict:
    """AI优化：收集用户确定的地点，调用大模型重新规划整个行程。
    AI会保留这些地点，但重新安排顺序和时间，确保往返时间合理。"""
    days = (db.query(TripDay)
            .filter(TripDay.trip_id == trip.id)
            .order_by(TripDay.day_no)
            .all())
    if not days:
        raise ValueError('行程没有天数记录')

    # 获取用户画像
    user = db.query(User).filter(User.id == trip.user_id).first() if trip.user_id else None

    # 收集用户确定的所有地点（去重）
    all_nodes = (db.query(ItineraryNode)
                 .filter(ItineraryNode.trip_id == trip.id)
                 .order_by(ItineraryNode.day_id, ItineraryNode.sort_order)
                 .all())
    user_pois = []
    seen_names = set()
    for n in all_nodes:
        name = n.name.strip()
        if name and name not in seen_names:
            seen_names.add(name)
            type_name = {'hotel': '酒店', 'attraction': '景点', 'restaurant': '餐厅', 'station': '交通枢纽'}.get(n.node_type, '景点')
            user_pois.append(f"{name}（{type_name}）")

    # 构建优化prompt
    prompt = _build_replan_prompt(trip, days, user_pois, user=user)
    messages = [{'role': 'user', 'content': prompt}]

    try:
        result = llm_service.chat_json(db, messages, temperature=0.7, max_tokens=2000, timeout=90)
    except Exception as e:
        # 大模型失败时降级为确定性重排
        return _deterministic_replan(db, trip)

    ai_days = result.get('days', [])
    if not ai_days:
        return _deterministic_replan(db, trip)

    # 清空已有节点和边
    db.query(ItineraryEdge).filter(ItineraryEdge.trip_id == trip.id).delete()
    db.query(ItineraryNode).filter(ItineraryNode.trip_id == trip.id).delete()
    db.flush()

    total_nodes = 0
    for day in days:
        city = day.city or trip.dest_city
        ai_day = None
        for ad in ai_days:
            if ad.get('day_no') == day.day_no:
                ai_day = ad
                break
        if not ai_day and ai_days:
            idx = day.day_no - 1
            if 0 <= idx < len(ai_days):
                ai_day = ai_days[idx]

        nodes_data = (ai_day or {}).get('nodes', [])
        if not nodes_data:
            nodes_data = ai_planner._fallback_nodes(city, day.day_no, trip.total_days,
                                                     trip.arrive_station, trip.depart_station)

        sort_order = 1
        for nd in nodes_data:
            name = (nd.get('name') or '').strip()
            if not name:
                continue
            ntype = ai_planner._normalize_type(nd.get('type', ''))
            duration = int(nd.get('duration_minutes', 60))
            if ntype == 'hotel':
                duration = 0
            if ntype == 'station':
                duration = 0
            node_city = (nd.get('city') or city).strip()
            note = (nd.get('note') or '').strip()

            poi = ai_planner._match_poi(db, name, node_city, ntype)
            node = ItineraryNode(
                trip_id=trip.id,
                day_id=day.id,
                city=node_city,
                poi_id=poi.id if poi else None,
                node_type=ntype,
                name=name,
                duration_minutes=duration,
                sort_order=sort_order,
                note=note,
            )
            db.add(node)
            sort_order += 1
            total_nodes += 1

    db.flush()

    # 给到达站和出发站设置固定start_time
    transport_lead = {'plane': 120, 'train': 60, 'ship': 90, 'car': 0}
    return_lead = transport_lead.get(trip.return_transport, 120)
    for day in days:
        siblings = (db.query(ItineraryNode)
                    .filter(ItineraryNode.day_id == day.id)
                    .order_by(ItineraryNode.sort_order, ItineraryNode.id)
                    .all())
        stations = [n for n in siblings if n.node_type == 'station']
        if day.day_no == 1 and trip.arrive_time and stations:
            stations[0].start_time = trip.arrive_time
        if day.day_no == trip.total_days and trip.depart_time and stations:
            depart_station = stations[-1]
            depart_station.start_time = (dt.datetime.combine(dt.date.today(), trip.depart_time) - dt.timedelta(minutes=return_lead)).time()

    # 重建边
    for day in days:
        ordered = (db.query(ItineraryNode)
                   .filter(ItineraryNode.day_id == day.id)
                   .order_by(ItineraryNode.sort_order)
                   .all())
        seed_planner._rebuild_day_edges(db, trip.id, day.id, ordered)

    db.commit()

    # 后处理：调整最后一天时间，避免太早去机场/车站
    timing_adjust = seed_planner.adjust_last_day_timing(db, trip)

    notes = [f"保留地点：{'、'.join(user_pois[:8])}{'...' if len(user_pois) > 8 else ''}"]
    if timing_adjust.get('adjusted'):
        notes.append(f"时间优化：{timing_adjust.get('reason', '')}")

    return {
        "applied": True,
        "summary": f"AI已根据您选择的{len(user_pois)}个地点重新规划行程，共{total_nodes}个节点",
        "notes": notes,
    }


def _build_replan_prompt(trip: Trip, days: list[TripDay], user_pois: list[str], user: User | None = None) -> str:
    """构建AI优化prompt：要求AI保留用户地点，重新规划顺序和时间。"""
    cities = [d.city or trip.dest_city for d in days]
    city_summary = '、'.join(sorted(set(cities)))
    if len(set(cities)) > 1:
        city_detail = '，'.join('第%d天=%s' % (i + 1, c) for i, c in enumerate(cities))
    else:
        city_detail = city_summary

    transport_names = {'plane': '飞机', 'train': '高铁', 'ship': '客轮', 'car': '自驾'}

    lines = [
        '你是一个专业的旅游行程规划助手。用户已经初步选择了想去的地点，请根据以下信息重新规划合理的行程顺序和时间安排。',
        '',
        '【行程信息】',
        '- 目的地：%s' % city_detail,
        '- 总天数：%d 天' % trip.total_days,
        '- 出发地：%s' % trip.depart_city,
    ]
    if trip.arrive_time:
        lines.append('- 第一天到达时间：%s（必须在此之后开始行程）' % trip.arrive_time.strftime('%H:%M'))
    if trip.depart_transport:
        lines.append('- 去程交通：%s%s' % (
            transport_names.get(trip.depart_transport, trip.depart_transport),
            '，到达%s' % trip.arrive_station if trip.arrive_station else ''))
    if trip.depart_time:
        lines.append('- 最后一天返程时间：%s（必须在此之前到达出发站）' % trip.depart_time.strftime('%H:%M'))
    if trip.return_transport:
        lines.append('- 返程交通：%s%s' % (
            transport_names.get(trip.return_transport, trip.return_transport),
            '，从%s出发' % trip.depart_station if trip.depart_station else ''))

    # 出行类型
    if trip.preferences and isinstance(trip.preferences, dict):
        travel_type = trip.preferences.get('travel_type')
        if travel_type:
            type_names = {'solo': '单人游', 'companion': '结伴游', 'family': '家庭游'}
            type_name = type_names.get(travel_type, travel_type)
            lines.append('- 出行类型：%s' % type_name)
            if travel_type == 'solo':
                lines.append('  - 单人游：可安排更多自由探索时间，推荐青旅或特色民宿，行程可更灵活')
            elif travel_type == 'companion':
                lines.append('  - 结伴游：适合互动性强的景点和活动，推荐双人房，可安排一些共同体验项目')
            elif travel_type == 'family':
                lines.append('  - 家庭游：行程节奏放缓，推荐亲子友好景点，避免过于劳累，餐厅选择要适合全家')

    # 用户画像
    if user:
        profile_parts = []
        if user.gender:
            profile_parts.append('性别：%s' % user.gender)
        if user.age:
            profile_parts.append('年龄：%d岁' % user.age)
        if user.identity:
            profile_parts.append('身份：%s' % user.identity)
        if user.preferences:
            if isinstance(user.preferences, list):
                profile_parts.append('喜好：%s' % '、'.join(user.preferences))
            elif isinstance(user.preferences, dict):
                import json
                profile_parts.append('喜好：%s' % json.dumps(user.preferences, ensure_ascii=False))
        if profile_parts:
            lines.append('')
            lines.append('【用户画像】')
            for p in profile_parts:
                lines.append('- %s' % p)
            lines.append('请根据用户画像调整行程：美食爱好者多安排特色餐厅，购物爱好者安排商圈，摄影爱好者推荐拍照点，退休人员节奏放缓，学生推荐性价比高的选择。')

    lines += [
        '',
        '【用户已选择的地点】',
        '以下地点必须包含在行程中（可调整顺序和分配到不同天）：',
    ]
    for i, p in enumerate(user_pois, 1):
        lines.append(f'{i}. {p}')

    lines += [
        '',
        '【规划要求】',
        '1. 必须包含上述所有用户选择的地点，可根据地理位置合理分配到不同天',
        '2. 每天安排 3-6 个节点，类型只能是 hotel（酒店）、attraction（景点）、restaurant（餐厅）、station（交通枢纽）',
        '3. 除到达日外，每天第一个节点必须是酒店（表示从酒店出发），最后一个节点通常是酒店；到达日第一个是交通站、最后一个是酒店；离开日第一个是酒店、最后一个是出发站，且出发站的时间应接近返程时间（飞机提前2小时、高铁提前1小时到达），不要太早去机场/车站',
        '4. 跨城天（当天从A城市到B城市）的节点顺序必须是：A城市出发站→B城市到达站→B城市酒店/景点',
        '5. 交通枢纽节点名称必须是简洁的车站/机场名称，如"太原南站"、"大同南站"，不能是"服务中心"、"宿舍楼"、"售票处"、"游客中心"等附属设施；景点名称不要带"售票处"、"景区入口"等后缀',
        '6. 餐厅应安排在中午和晚上的用餐时间附近',
        '7. 合理安排每个景点的停留时间，确保最后一天能赶上返程交通',
        '8. duration_minutes 为建议停留分钟数，酒店和交通站点设为 0',
        '9. city 字段必填，填写该节点实际所在城市',
        '10. 用户已选择的地点必须全部保留，可根据地理位置和时间安排调整顺序、分配到不同天；在此基础上，AI可以根据专业判断适当增加景点、餐厅等节点，使行程更丰富合理，但不要过度堆砌',
        '',
        '【输出格式】严格输出 JSON，不要输出任何其他文字：',
        '{',
        '  "days": [',
        '    {"day_no": 1, "nodes": [{"name": "...", "type": "hotel|attraction|restaurant|station", "city": "城市名", "duration_minutes": 120, "note": "..."}]},',
        '    {"day_no": 2, "nodes": [...]},',
        '  ]',
        '}',
    ]
    return '\n'.join(lines)


def _deterministic_replan(db: Session, trip: Trip) -> dict:
    """降级方案：确定性重排（大模型不可用时使用）。"""
    notes: list[str] = []
    changed_days = 0

    days = (db.query(TripDay)
            .filter(TripDay.trip_id == trip.id)
            .order_by(TripDay.day_no)
            .all())

    for day in days:
        nodes = (db.query(ItineraryNode)
                 .filter(ItineraryNode.day_id == day.id)
                 .order_by(ItineraryNode.sort_order)
                 .all())
        for n in nodes:
            n.poi = db.get(Poi, n.poi_id) if n.poi_id else None

        if len(nodes) <= 3:
            continue

        head, tail = nodes[0], nodes[-1]
        middle = nodes[1:-1]

        before = [n.id for n in middle]
        ranked = sorted(middle, key=lambda n: -_rating(n))
        ranked = _interleave(ranked)
        after = [n.id for n in ranked]
        moved = [n for n in ranked if n.id not in before or before.index(n.id) != after.index(n.id)]

        _apply_order(db, day, [head] + ranked + [tail])
        day_notes = []

        tl = seed_planner.compute_day_timeline(db, day)
        tl_nodes = tl["nodes"]
        swapped = True
        guard = 0
        while swapped and guard < len(tl_nodes):
            swapped = False
            guard += 1
            tl = seed_planner.compute_day_timeline(db, day)
            tl_nodes = tl["nodes"]
            for i in range(len(tl_nodes) - 1):
                n = tl_nodes[i]
                w = _open_window(n.get("poi"))
                if not w:
                    continue
                open_t = _fmt_mm(w[0])
                start_t = _fmt_mm(dt.time.fromisoformat(n["start_time"]))
                if start_t < open_t:
                    cur = db.get(ItineraryNode, n["id"])
                    nxt = db.get(ItineraryNode, tl_nodes[i + 1]["id"])
                    cur.sort_order, nxt.sort_order = nxt.sort_order, cur.sort_order
                    _rebuild_from_db(db, day)
                    tl2 = seed_planner.compute_day_timeline(db, day)
                    n2 = next((x for x in tl2["nodes"] if x["id"] == n["id"]), None)
                    ok = n2 and _fmt_mm(dt.time.fromisoformat(n2["start_time"])) >= open_t
                    if ok:
                        day_notes.append(
                            f"D{day.day_no}：「{n['name']}」营业 {w[0].strftime('%H:%M')} 开门，已调整到开门后安排")
                        swapped = True
                        break
                    cur.sort_order, nxt.sort_order = nxt.sort_order, cur.sort_order
                    _rebuild_from_db(db, day)
                    break

        for n in moved:
            if _rating(n) > 0:
                day_notes.append(f"D{day.day_no}：「{n.name}」评分 {_rating(n):.1f}，已优先安排")
            else:
                day_notes.append(f"D{day.day_no}：「{n.name}」为占位节点，已置于评分节点之后")

        if day_notes:
            changed_days += 1
            notes.extend(day_notes[:4])

    db.commit()
    summary = f"已按评分、类型分布与营业时间重排 {changed_days} 天"
    return {"applied": True, "summary": summary, "notes": notes}
