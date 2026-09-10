# -*- coding: utf-8 -*-
"""高德地图 POI 搜索服务：关键词搜索 → 转换为内部 Poi → 入库（source='gaode'）。"""
import json
import urllib.parse
import urllib.request
from sqlalchemy.orm import Session
from ..models import Poi
from ..services.setting_service import get_value

AMAP_POI_URL = "https://restapi.amap.com/v3/place/text"

# 高德类型关键词 → 内部 poi_type 映射
_TYPE_KEYWORDS = {
    "hotel": ["酒店", "宾馆", "旅馆", "民宿", "客栈", "住宿", "度假村"],
    "restaurant": ["餐厅", "餐饮", "美食", "小吃", "快餐", "火锅", "烧烤", "咖啡", "茶馆", "酒吧", "食堂", "把子肉", "面馆"],
    "attraction": ["景点", "景区", "公园", "广场", "博物馆", "纪念馆", "寺庙", "塔", "湖", "山", "古镇", "古城", "游乐园", "动物园"],
}


def _guess_poi_type(name: str, amap_type: str) -> str:
    """根据名称和高德类型猜测内部 poi_type。"""
    text = (name or "") + (amap_type or "")
    for ptype, keywords in _TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return ptype
    return "attraction"  # 默认景点


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

        # 查是否已存在（同城市+同名称+同类型）
        existing = (db.query(Poi)
                    .filter(Poi.name == name, Poi.city == (city or ""),
                            Poi.poi_type == ptype)
                    .first())
        if existing:
            # 更新缺失字段
            if not existing.address and item.get("address"):
                existing.address = item["address"]
            if not existing.rating and rating:
                try:
                    existing.rating = float(rating)
                except (ValueError, TypeError):
                    pass
            if not existing.ticket_price and ticket_price:
                existing.ticket_price = ticket_price
            if not existing.lat and lat:
                existing.lat = lat
                existing.lng = lng
            if not existing.source:
                existing.source = "gaode"
            results.append(existing)
            continue

        poi = Poi(
            city=city or "",
            poi_type=ptype,
            name=name,
            address=item.get("address"),
            open_hours=None,  # 高德开放平台基础版不返回营业时间
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
