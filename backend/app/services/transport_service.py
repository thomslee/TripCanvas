# -*- coding: utf-8 -*-
"""交通方式与耗时计算：根据两点间距离推断默认交通方式和时间。"""
import math
from sqlalchemy.orm import Session
from ..models import ItineraryNode, Poi

# 交通方式默认速度（km/h）
TRANSPORT_SPEEDS = {
    "walk": 5.0,      # 步行
    "bike": 15.0,     # 骑行
    "taxi": 25.0,     # 打车（城市道路）
    "car": 30.0,      # 自驾（城市道路）
    "bus": 18.0,      # 公交
    "metro": 35.0,    # 地铁
}

# 距离阈值（km）
WALK_THRESHOLD = 1.0  # 1公里内默认步行


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """计算两点间直线距离（公里）。"""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_node_coords(db: Session, node: ItineraryNode) -> tuple[float | None, float | None]:
    """获取节点经纬度：优先用节点自身的 lat/lng，否则用关联 POI 的。"""
    if node.lat and node.lng:
        return float(node.lat), float(node.lng)
    if node.poi_id:
        poi = db.query(Poi).filter(Poi.id == node.poi_id).first()
        if poi and poi.lat and poi.lng:
            return float(poi.lat), float(poi.lng)
    return None, None


def infer_transport(db: Session, from_node: ItineraryNode, to_node: ItineraryNode) -> tuple[str, int, float | None]:
    """根据两节点距离推断交通方式和耗时。

    返回 (transport, duration_minutes, distance_km)。
    无法获取坐标时返回默认自驾 30 分钟。
    """
    lat1, lng1 = get_node_coords(db, from_node)
    lat2, lng2 = get_node_coords(db, to_node)

    if lat1 is None or lat2 is None:
        # 无法计算距离，默认自驾 30 分钟
        return "car", 30, None

    distance = haversine_km(lat1, lng1, lat2, lng2)

    # 距离极近（<50米）视为同一地点，步行 2 分钟
    if distance < 0.05:
        return "walk", 2, round(distance, 2)

    # 1公里内步行，1公里以上自驾
    if distance < WALK_THRESHOLD:
        transport = "walk"
    else:
        transport = "car"

    speed = TRANSPORT_SPEEDS.get(transport, 30.0)
    duration = max(1, int(round(distance / speed * 60)))

    return transport, duration, round(distance, 2)
