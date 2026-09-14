# -*- coding: utf-8 -*-
"""AI 行程规划引擎：调用大模型生成每日节点安排。"""
import json
import datetime
from sqlalchemy.orm import Session
from ..models import Trip, TripDay, ItineraryNode, ItineraryEdge, Poi, User
from ..services import llm_service, seed_planner

_TYPE_MAP = {
    '景点': 'attraction', '景区': 'attraction', '公园': 'attraction',
    '餐厅': 'restaurant', '美食': 'restaurant', '吃饭': 'restaurant',
    '酒店': 'hotel', '住宿': 'hotel', '客栈': 'hotel', '民宿': 'hotel',
    '高铁站': 'station', '火车站': 'station', '动车站': 'station', '车站': 'station',
    '机场': 'station', '航站楼': 'station', '汽车站': 'station', '客运中心': 'station',
    '码头': 'station', '港口': 'station', '客运站': 'station',
}
_VALID_TYPES = {'hotel', 'attraction', 'restaurant', 'station'}


def _build_prompt(trip: Trip, days: list[TripDay], user: User | None = None) -> str:
    """构建行程规划 prompt。"""
    cities = [d.city or trip.dest_city for d in days]
    city_summary = '、'.join(sorted(set(cities)))
    if len(set(cities)) > 1:
        city_detail = '，'.join('第%d天=%s' % (i + 1, c) for i, c in enumerate(cities))
    else:
        city_detail = city_summary

    transport_names = {'plane': '飞机', 'train': '高铁', 'ship': '客轮', 'car': '自驾'}

    lines = [
        '你是一个专业的旅游行程规划助手。请根据以下信息生成详细的每日行程安排。',
        '',
        '【行程信息】',
        '- 目的地：%s' % city_detail,
        '- 总天数：%d 天' % trip.total_days,
        '- 出发地：%s' % trip.depart_city,
    ]
    if trip.arrive_time:
        lines.append('- 第一天到达时间：%s' % trip.arrive_time.strftime('%H:%M'))
    if trip.depart_transport:
        lines.append('- 去程交通：%s%s' % (
            transport_names.get(trip.depart_transport, trip.depart_transport),
            '，到达%s' % trip.arrive_station if trip.arrive_station else ''))
    if trip.depart_time:
        lines.append('- 最后一天返程时间：%s' % trip.depart_time.strftime('%H:%M'))
    if trip.return_transport:
        lines.append('- 返程交通：%s%s' % (
            transport_names.get(trip.return_transport, trip.return_transport),
            '，从%s出发' % trip.depart_station if trip.depart_station else ''))
    if trip.preferences:
        prefs = trip.preferences
        if isinstance(prefs, dict):
            req = prefs.get('requirements') or prefs.get('travel_requirements')
            if req:
                lines.append('- 旅游要求：%s' % req)
            # 出行类型特殊处理
            travel_type = prefs.get('travel_type')
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
            for k, v in prefs.items():
                if k not in ('requirements', 'travel_requirements', 'travel_type'):
                    lines.append('- %s：%s' % (k, v))
        else:
            lines.append('- 用户偏好：%s' % json.dumps(prefs, ensure_ascii=False))

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
                profile_parts.append('喜好：%s' % json.dumps(user.preferences, ensure_ascii=False))
        if profile_parts:
            lines.append('')
            lines.append('【用户画像】')
            for p in profile_parts:
                lines.append('- %s' % p)
            lines.append('')
            lines.append('请根据用户画像调整行程：')
            lines.append('- 美食爱好者：每天至少安排1-2个当地特色餐厅')
            lines.append('- 购物爱好者：适当安排商圈、夜市')
            lines.append('- 摄影爱好者：推荐适合拍照的景点和时间')
            lines.append('- 历史文化爱好者：优先推荐博物馆、古迹')
            lines.append('- 自然风光爱好者：优先推荐自然景观')
            lines.append('- 学生：推荐性价比高的住宿和餐饮')
            lines.append('- 退休：行程节奏放缓，避免长时间步行和过于紧凑的安排')
            lines.append('- 根据年龄调整行程强度，年龄较大者需要更多休息时间')

    lines += [
        '',
        '【输出要求】',
        '1. 每天安排 3-6 个节点，类型只能是 hotel（酒店）、attraction（景点）、restaurant（餐厅）、station（交通枢纽：高铁站/机场/火车站/码头）',
        '2. 到达日（第1天）第一个节点应为到达的交通站点（station），如"丽江三义机场"、"济南西站"，然后是酒店；离开日最后一个节点应为出发的交通站点（station），且出发站的时间应接近返程时间（飞机提前2小时、高铁提前1小时到达），不要太早去机场/车站',
        '3. 除到达日外，每天第一个节点必须是酒店（表示从酒店出发），最后一个节点通常是酒店；到达日第一个是交通站、最后一个是酒店；离开日第一个是酒店、最后一个是出发站',
        '4. 跨城天（当天从A城市到B城市）的节点顺序必须是：A城市出发站（station，如"太原南站"）→ B城市到达站（station，如"大同南站"）→ B城市酒店/景点，绝对不能把前一天的酒店作为跨城天的第一个节点',
        '5. 交通枢纽节点名称必须是简洁的车站/机场名称，如"太原南站"、"大同南站"、"杭州萧山国际机场"，绝对不能是"高铁服务中心"、"高铁站宿舍楼"、"机场酒店"、"售票处"、"游客中心"等附属设施名称；景点名称不要带"售票处"、"景区入口"等后缀',
        '6. 餐厅应安排在中午和晚上的用餐时间附近',
        '7. duration_minutes 为建议停留分钟数，酒店和交通站点设为 0',
        '8. 节点名称要具体真实，如"大理古城"、"洱海边"、"白族风味餐厅"、"丽江三义机场"',
        '9. note 字段可选，写一句简短的游玩建议或推荐理由',
        '10. city 字段必填，填写该节点实际所在城市，跨城天（一天内涉及两个城市）要根据节点顺序正确标注，如上午在太原、下午到大同，则太原的节点city="太原"，大同的节点city="大同"',
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


def _match_poi(db: Session, name: str, city: str, node_type: str) -> Poi | None:
    """AI生成时只匹配ai来源的POI，不匹配高德POI，确保用户看到的都是AI推荐名称。
    排除包含服务中心/宿舍楼等非主体设施词的POI。
    未匹配则创建 AI 来源的自定义 POI。"""
    if not name or len(name) < 2:
        return None
    # 排除非主体设施词
    exclude_kw = ["服务中心", "宿舍楼", "酒店", "宾馆", "餐厅", "饭店", "小吃", "超市", "商店", "停车场", "售票处", "便利店", "咖啡", "茶馆", "酒吧", "宿舍", "公寓", "住宅", "小区"]
    # 只匹配ai来源的POI，避免匹配到高德来源的错误POI
    pois = db.query(Poi).filter(Poi.poi_type == node_type, Poi.source == 'ai').all()
    # 优先匹配城市 + 名称包含，且排除非主体设施
    for p in pois:
        if p.city and city and p.city != city:
            continue
        if node_type == 'station' and any(kw in p.name for kw in exclude_kw):
            continue
        if name in p.name or p.name in name:
            return p
    # 放宽：不限制城市
    for p in pois:
        if node_type == 'station' and any(kw in p.name for kw in exclude_kw):
            continue
        if name in p.name or p.name in name:
            return p
    # 未匹配：创建 AI 来源的自定义 POI
    poi = Poi(
        city=city,
        poi_type=node_type,
        name=name,
        source='ai',
    )
    db.add(poi)
    db.flush()
    return poi


def _normalize_type(t: str) -> str:
    t = (t or '').strip().lower()
    if t in _VALID_TYPES:
        return t
    for cn, en in _TYPE_MAP.items():
        if cn in t:
            return en
    return 'attraction'


def ai_plan_trip(db: Session, trip: Trip) -> dict:
    """调用大模型生成行程节点，写入数据库。返回生成统计。"""
    days = (db.query(TripDay)
            .filter(TripDay.trip_id == trip.id)
            .order_by(TripDay.day_no)
            .all())
    if not days:
        raise ValueError('行程没有天数记录')

    # 获取用户画像
    user = db.query(User).filter(User.id == trip.user_id).first() if trip.user_id else None

    # 清空已有节点和边
    db.query(ItineraryEdge).filter(ItineraryEdge.trip_id == trip.id).delete()
    db.query(ItineraryNode).filter(ItineraryNode.trip_id == trip.id).delete()
    db.flush()

    prompt = _build_prompt(trip, days, user=user)
    messages = [{'role': 'user', 'content': prompt}]
    result = llm_service.chat_json(db, messages, temperature=0.8, max_tokens=2000, timeout=90)

    ai_days = result.get('days', [])
    total_nodes = 0
    poi_matched = 0
    created_nodes = []

    for day in days:
        city = day.city or trip.dest_city
        # 找大模型返回的对应天
        ai_day = None
        for ad in ai_days:
            if ad.get('day_no') == day.day_no:
                ai_day = ad
                break
        if not ai_day and ai_days:
            # 按索引 fallback
            idx = day.day_no - 1
            if 0 <= idx < len(ai_days):
                ai_day = ai_days[idx]

        nodes_data = (ai_day or {}).get('nodes', [])
        if not nodes_data:
            # 降级：用种子骨架的模板
            nodes_data = _fallback_nodes(city, day.day_no, trip.total_days,
                                         trip.arrive_station, trip.depart_station)

        sort_order = 1
        for nd in nodes_data:
            name = (nd.get('name') or '').strip()
            if not name:
                continue
            ntype = _normalize_type(nd.get('type', ''))
            duration = int(nd.get('duration_minutes', 60))
            if ntype == 'hotel':
                duration = 0
            note = (nd.get('note') or '').strip() or None
            # 节点城市：优先用AI返回的city，否则用当天城市
            node_city = (nd.get('city') or '').strip() or city

            # 匹配真实 POI（用节点所在城市搜索）
            poi = _match_poi(db, name, node_city, ntype)
            if poi:
                name = poi.name
                poi_matched += 1

            node = ItineraryNode(
                trip_id=trip.id,
                day_id=day.id,
                city=node_city,
                node_type=ntype,
                name=name,
                duration_minutes=duration,
                sort_order=sort_order,
                note=note,
                poi_id=poi.id if poi else None,
            )
            db.add(node)
            created_nodes.append(node)
            sort_order += 1
            total_nodes += 1

    db.flush()

    # 给到达站和出发站设置固定start_time，确保时间合理
    # 到达站：第一天第一个station节点，start_time = arrive_time
    # 出发站：最后一天最后一个station节点，start_time = depart_time - 提前量
    transport_lead = {'plane': 120, 'train': 60, 'ship': 90, 'car': 0}
    return_lead = transport_lead.get(trip.return_transport, 120)
    for day in days:
        siblings = (db.query(ItineraryNode)
                    .filter(ItineraryNode.day_id == day.id)
                    .order_by(ItineraryNode.sort_order, ItineraryNode.id)
                    .all())
        stations = [n for n in siblings if n.node_type == 'station']
        if day.day_no == 1 and trip.arrive_time and stations:
            # 第一天第一个station是到达站
            stations[0].start_time = trip.arrive_time
        if day.day_no == trip.total_days and trip.depart_time and stations:
            # 最后一天最后一个station是出发站
            depart_station = stations[-1]
            from datetime import timedelta
            depart_station.start_time = (datetime.datetime.combine(datetime.date.today(), trip.depart_time) - timedelta(minutes=return_lead)).time()

    # 重建每天的边
    for day in days:
        siblings = (db.query(ItineraryNode)
                    .filter(ItineraryNode.day_id == day.id)
                    .order_by(ItineraryNode.sort_order, ItineraryNode.id)
                    .all())
        seed_planner._rebuild_day_edges(db, trip.id, day.id, siblings)

    db.commit()

    # 后处理：调整最后一天时间，避免太早去机场/车站
    timing_adjust = seed_planner.adjust_last_day_timing(db, trip)

    return {
        'generated': True,
        'total_nodes': total_nodes,
        'poi_matched': poi_matched,
        'days': len(days),
        'source': 'ai',
        'timing_adjusted': timing_adjust.get('adjusted', False),
        'timing_note': timing_adjust.get('reason', ''),
    }


def _fallback_nodes(city: str, day_no: int, total_days: int,
                    arrive_station: str | None = None, depart_station: str | None = None) -> list[dict]:
    """大模型返回为空时的降级模板。"""
    is_first = day_no == 1
    is_last = day_no == total_days
    nodes = []
    if is_first:
        if arrive_station:
            nodes.append({'name': arrive_station, 'type': 'station', 'duration_minutes': 0})
        nodes += [
            {'name': '%s酒店' % city, 'type': 'hotel', 'duration_minutes': 0},
            {'name': '%s古城' % city, 'type': 'attraction', 'duration_minutes': 120},
            {'name': '当地特色餐厅', 'type': 'restaurant', 'duration_minutes': 60},
        ]
    elif is_last:
        nodes = [
            {'name': '%s酒店' % city, 'type': 'hotel', 'duration_minutes': 0},
            {'name': '周边景点', 'type': 'attraction', 'duration_minutes': 90},
            {'name': '当地特色餐厅', 'type': 'restaurant', 'duration_minutes': 60},
        ]
        if depart_station:
            nodes.append({'name': depart_station, 'type': 'station', 'duration_minutes': 0})
    else:
        nodes = [
            {'name': '%s酒店' % city, 'type': 'hotel', 'duration_minutes': 0},
            {'name': '主要景点A', 'type': 'attraction', 'duration_minutes': 120},
            {'name': '午餐餐厅', 'type': 'restaurant', 'duration_minutes': 60},
            {'name': '主要景点B', 'type': 'attraction', 'duration_minutes': 120},
            {'name': '晚餐餐厅', 'type': 'restaurant', 'duration_minutes': 60},
            {'name': '%s酒店' % city, 'type': 'hotel', 'duration_minutes': 0},
        ]
    return nodes
