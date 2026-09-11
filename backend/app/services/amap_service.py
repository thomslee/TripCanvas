# -*- coding: utf-8 -*-
"""高德地图 POI 搜索服务：关键词搜索 → 转换为内部 Poi → 入库（source='gaode'）。"""
import json
import time
import urllib.parse
import urllib.request
from sqlalchemy.orm import Session
from ..models import Poi, ItineraryNode, Trip
from ..services.setting_service import get_value

AMAP_POI_URL = "https://restapi.amap.com/v3/place/text"

# 高德类型关键词 → 内部 poi_type 映射
_TYPE_KEYWORDS = {
    "station": ["高铁站", "火车站", "动车站", "车站", "机场", "航站楼", "汽车站", "客运中心", "码头", "港口", "客运站", "进站口", "出站口", "地铁站", "轻轨站", "东站", "西站", "南站", "北站", "站"],
    "hotel": ["酒店", "宾馆", "旅馆", "民宿", "客栈", "住宿", "度假村"],
    "restaurant": ["餐厅", "餐饮", "美食", "小吃", "快餐", "火锅", "烧烤", "咖啡", "茶馆", "酒吧", "食堂", "把子肉", "面馆", "饭店", "菜馆", "食府"],
    "attraction": ["景点", "景区", "公园", "广场", "博物馆", "纪念馆", "寺庙", "塔", "湖", "古镇", "古城", "游乐园", "动物园", "山岳", "山脉", "风景区", "森林公园", "地质公园"],
}


def _guess_poi_type(name: str, amap_type: str) -> str:
    """根据名称和高德类型猜测内部 poi_type。"""
    text = (name or "") + (amap_type or "")
    # 明确的住宿类优先：如果名称包含酒店/宾馆/客栈等，即使含机场/车站也判为hotel
    hotel_kw = ["酒店", "宾馆", "旅馆", "民宿", "客栈", "住宿", "度假村", "饭店", "大酒店", "酒店式公寓", "公寓"]
    for kw in hotel_kw:
        if kw in text:
            return "hotel"
    # 明确的餐饮类优先
    restaurant_kw = ["餐厅", "餐饮", "美食", "小吃", "快餐", "火锅", "烧烤", "咖啡", "茶馆", "酒吧", "食堂", "面馆", "菜馆", "食府", "饭店"]
    for kw in restaurant_kw:
        if kw in text and "酒店" not in text and "宾馆" not in text:
            return "restaurant"
    # 交通枢纽
    for kw in _TYPE_KEYWORDS.get("station", []):
        if kw in text:
            return "station"
    # 景点
    for kw in _TYPE_KEYWORDS.get("attraction", []):
        if kw in text:
            return "attraction"
    return "attraction"  # 默认景点


def _pick_best_match(target_name: str, candidates: list, node_type: str) -> object:
    """从候选POI中选择最佳匹配。

    优先级：
    1. 名称完全一致
    2. 名称简洁（排除服务中心/宿舍楼/酒店/餐厅等非主体设施）
    3. 名称相似度最高
    """
    if not candidates:
        return None

    # station类型排除非主体设施（服务中心/宿舍楼/酒店等）
    exclude_kw = ["服务中心", "宿舍楼", "酒店", "宾馆", "餐厅", "饭店", "小吃", "超市", "商店", "停车场", "售票处", "便利店", "咖啡", "茶馆", "酒吧", "宿舍", "公寓", "住宅", "小区"]
    if node_type == "station":
        main_candidates = [p for p in candidates if not any(kw in p.name for kw in exclude_kw)]
        if main_candidates:
            candidates = main_candidates
        else:
            # station类型没有干净候选时不替换，避免匹配到宿舍楼/服务中心等
            return None

    # 1. 名称完全一致
    exact = next((p for p in candidates if p.name == target_name), None)
    if exact:
        return exact

    # 2. 名称以目标名称开头或结尾（如"太原南站" vs "太原南站"）
    prefix_match = next((p for p in candidates if p.name.startswith(target_name) or p.name.endswith(target_name)), None)
    if prefix_match:
        return prefix_match

    # 3. 目标名称包含在POI名称中，选最短的（最简洁的）
    contains = [p for p in candidates if target_name in p.name]
    if contains:
        return min(contains, key=lambda p: len(p.name))

    # 4. 按名称长度差异排序，选最接近的
    return min(candidates, key=lambda p: abs(len(p.name) - len(target_name)))


def search_pois(db: Session, keyword: str, city: str | None = None,
                limit: int = 15) -> list[Poi]:
    """从高德搜索 POI，转换并存入数据库（去重），返回 Poi 列表。"""
    key = get_value(db, "amap_key") or ""
    if not key or key == "amap-test":
        return []

    params = {
        "keywords": keyword,
        "key": key,
        "offset": str(limit),
        "page": "1",
        "extensions": "all",
    }
    if city:
        params["city"] = city
        params["citylimit"] = "true"

    url = AMAP_POI_URL + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TripCanvas/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []

    if data.get("status") != "1":
        return []

    results = []
    for item in data.get("pois", []):
        name = item.get("name", "").strip()
        if not name:
            continue

        # address 可能是列表或字符串，统一转为字符串
        addr = item.get("address")
        if isinstance(addr, list):
            addr = addr[0] if addr else ""
        elif not isinstance(addr, str):
            addr = str(addr) if addr else None

        # 经纬度
        lat = lng = None
        loc = item.get("location", "")
        if loc and "," in loc:
            try:
                lng_str, lat_str = loc.split(",", 1)
                lng = float(lng_str)
                lat = float(lat_str)
            except (ValueError, TypeError):
                pass

        # 评分和人均
        biz_ext = item.get("biz_ext") or {}
        rating = biz_ext.get("rating")
        cost = biz_ext.get("cost")
        phone = item.get("tel") or None
        ticket_price = None
        if cost:
            try:
                c = float(cost)
                if c > 0:
                    ticket_price = "人均 ¥%.0f" % c
            except (ValueError, TypeError):
                pass

        amap_type = item.get("type", "")
        ptype = _guess_poi_type(name, amap_type)

        # 从高德返回结果提取实际城市（cityname如"杭州市"，去掉"市"）
        real_city = (item.get("cityname") or "").strip()
        if real_city.endswith("市"):
            real_city = real_city[:-1]
        # 如果高德没返回城市名，用传入的city
        poi_city = real_city or (city or "")

        # 查是否已存在（同城市+同名称+同类型）
        existing = (db.query(Poi)
                    .filter(Poi.name == name, Poi.city == poi_city,
                            Poi.poi_type == ptype)
                    .first())
        if existing:
            # 如果是 AI 来源的占位 POI，升级为高德真实 POI
            if existing.source == "ai":
                existing.source = "gaode"
                existing.city = poi_city
                existing.address = addr or existing.address
                existing.lat = lat or existing.lat
                existing.lng = lng or existing.lng
                if rating:
                    try:
                        existing.rating = float(rating)
                    except (ValueError, TypeError):
                        pass
                if ticket_price:
                    existing.ticket_price = ticket_price
                if phone:
                    existing.phone = phone
            else:
                # 已有真实 POI，仅补全缺失字段
                if not existing.city and poi_city:
                    existing.city = poi_city
                if not existing.address and addr:
                    existing.address = addr
                if not existing.rating and rating:
                    try:
                        existing.rating = float(rating)
                    except (ValueError, TypeError):
                        pass
                if not existing.ticket_price and ticket_price:
                    existing.ticket_price = ticket_price
                if not existing.phone and phone:
                    existing.phone = phone
                if not existing.lat and lat:
                    existing.lat = lat
                    existing.lng = lng
            results.append(existing)
            continue

        poi = Poi(
            city=poi_city,
            poi_type=ptype,
            name=name,
            address=addr or None,
            open_hours=None,  # 高德开放平台基础版不返回营业时间
            phone=phone,
            ticket_price=ticket_price,
            rating=float(rating) if rating else None,
            source="gaode",
            lat=lat,
            lng=lng,
        )
        db.add(poi)
        db.flush()
        results.append(poi)

    db.commit()
    return results


def auto_replace_pois(db: Session, trip: Trip) -> dict:
    """批量将行程中 AI 推荐的节点替换为高德真实 POI。

    遍历所有 source='ai' 的节点，用节点名称搜索高德，取同类型第一个结果替换。
    优先用节点自身的 city 字段（跨城天准确），否则用所在天的城市。
    返回 {replaced, failed, items: [{node_name, old, new, status}]}
    """
    from ..models.trip import TripDay
    # 找出所有 AI 推荐节点（poi.source == 'ai'），同时获取所在天的城市
    ai_nodes = (
        db.query(ItineraryNode, TripDay.city.label('day_city'))
        .join(Poi, ItineraryNode.poi_id == Poi.id)
        .join(TripDay, ItineraryNode.day_id == TripDay.id)
        .filter(ItineraryNode.trip_id == trip.id, Poi.source == "ai")
        .all()
    )
    if not ai_nodes:
        return {"replaced": 0, "failed": 0, "items": []}

    # 收集本次行程的所有目标城市（节点city + 天city，按天顺序去重）
    all_days = db.query(TripDay).filter(TripDay.trip_id == trip.id).order_by(TripDay.day_no).all()
    trip_cities: list[str] = []
    for d in all_days:
        if d.city and d.city not in trip_cities:
            trip_cities.append(d.city)
    if trip.dest_city and trip.dest_city not in trip_cities:
        trip_cities.append(trip.dest_city)

    # 按 (名称, 城市) 去重缓存，同名不同城可能匹配到不同结果
    name_cache: dict[tuple[str, str], Poi | None] = {}
    replaced = 0
    failed = 0
    items = []

    for node, day_city in ai_nodes:
        # 优先用节点自身的城市（跨城天准确），否则用当天城市
        city = node.city or day_city or trip.dest_city or ""
        name = node.name.strip()
        if not name:
            failed += 1
            items.append({"node_name": name, "old": name, "new": None, "status": "empty_name"})
            continue

        cache_key = (name, city)
        if cache_key in name_cache:
            matched = name_cache[cache_key]
        else:
            # 搜索高德，加类型后缀提高匹配率
            type_suffix = {"hotel": "酒店", "restaurant": "餐厅", "attraction": "", "station": ""}.get(node.node_type, "")
            keyword = name if any(k in name for k in ["酒店", "宾馆", "客栈", "餐厅", "饭店", "景区", "公园", "古镇", "古城"]) else name + type_suffix
            # 构建搜索城市顺序：当天城市优先，然后行程内其他目标城市依次
            search_cities = [city] if city else []
            for c in trip_cities:
                if c not in search_cities:
                    search_cities.append(c)
            matched = None
            try:
                for search_city in search_cities:
                    results = search_pois(db, keyword=keyword, city=search_city, limit=10)
                    real_results = [p for p in results if p.source in ("gaode", "seed")]
                    # 过滤：类型一致 + 城市一致
                    candidates = [p for p in real_results
                                  if p.poi_type == node.node_type
                                  and p.city
                                  and (p.city == city or p.city in city or city in p.city)]
                    if candidates:
                        matched = _pick_best_match(name, candidates, node.node_type)
                    if matched:
                        break
                    # 如果当前城市没找到，尝试缩短关键词（去掉"T3""航站楼"等后缀）
                    if not matched and any(k in keyword for k in ["T3", "T2", "T1", "航站楼", "国际机场"]):
                        short_kw = keyword.replace("T3", "").replace("T2", "").replace("T1", "").replace("航站楼", "").replace("国际机场", "机场").strip()
                        if short_kw and short_kw != keyword:
                            results2 = search_pois(db, keyword=short_kw, city=search_city, limit=10)
                            real2 = [p for p in results2 if p.source in ("gaode", "seed")]
                            candidates2 = [p for p in real2
                                           if p.poi_type == node.node_type
                                           and p.city
                                           and (p.city == city or p.city in city or city in p.city)]
                            if candidates2:
                                matched = _pick_best_match(name, candidates2, node.node_type)
                            if matched:
                                break
            except Exception:
                db.rollback()
                matched = None
            name_cache[cache_key] = matched
            time.sleep(0.1)  # 避免高德频控

        if matched:
            node.poi_id = matched.id
            node.name = matched.name  # 同步更新节点名称为真实POI名称
            replaced += 1
            items.append({"node_name": name, "old": name, "new": matched.name, "status": "ok"})
        else:
            failed += 1
            items.append({"node_name": name, "old": name, "new": None, "status": "not_found"})

    db.commit()
    return {"replaced": replaced, "failed": failed, "items": items}
