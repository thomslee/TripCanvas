# -*- coding: utf-8 -*-
"""距离与交通方式计算服务。

用 haversine 公式计算两点间直线距离，乘以路线系数估算实际距离；
按距离自动选择交通方式：<1km 步行，>=1km 打车。
"""
import math
from sqlalchemy.orm import Session
from ..models import ItineraryNode, Poi

# 交通方式默认速度（km/h）
TRANSPORT_SPEEDS = {
    "walk": 5.0,
    "bike": 12.0,
    "taxi": 25.0,
    "car": 30.0,
    "bus": 18.0,
    "metro": 35.0,
    "train": 200.0,  # 高铁
    "plane": 700.0,  # 飞机
}

# 距离阈值（km）
WALK_MAX_DISTANCE = 1.0
CROSS_CITY_TRAIN_MAX = 500.0  # 500km以内优先高铁

# 直线距离转实际路线距离的系数
ROUTE_FACTOR = 1.3


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """计算两点间直线距离（公里）。"""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_node_coords(db: Session, node: ItineraryNode) -> tuple[float, float] | None:
    """获取节点经纬度：优先用关联 POI，其次用节点自身。"""
    if node.poi_id:
        poi = db.query(Poi).filter(Poi.id == node.poi_id).first()
        if poi and poi.lat and poi.lng:
            return float(poi.lat), float(poi.lng)
    if node.lat and node.lng:
        return float(node.lat), float(node.lng)
    return None


def calc_transport(db: Session, from_node: ItineraryNode, to_node: ItineraryNode, default_transport: str = "taxi") -> dict:
    """计算两节点间的距离、交通方式和耗时。

    返回 {distance_km, transport, duration_minutes}。
    无法获取坐标时返回默认值（打车30分钟，距离None）。
    跨城（节点city不同）优先高铁/飞机，同城<1km步行，否则用default_transport。
    default_transport: 默认交通方式，自驾行程传"car"，其他传"taxi"。
    """
    c1 = get_node_coords(db, from_node)
    c2 = get_node_coords(db, to_node)

    if not c1 or not c2:
        return {"distance_km": None, "transport": default_transport, "duration_minutes": 30}

    straight = haversine_km(c1[0], c1[1], c2[0], c2[1])
    distance = round(straight * ROUTE_FACTOR, 2)

    # 判断是否跨城：节点城市不同，或距离超过50km
    from_city = (from_node.city or "").strip()
    to_city = (to_node.city or "").strip()
    is_cross_city = (from_city and to_city and from_city != to_city) or distance > 50

    if is_cross_city:
        # 跨城：500km以内高铁，以上飞机
        if distance <= CROSS_CITY_TRAIN_MAX:
            transport = "train"
        else:
            transport = "plane"
    elif distance < WALK_MAX_DISTANCE:
        transport = "walk"
    else:
        transport = default_transport

    speed = TRANSPORT_SPEEDS.get(transport, 25.0)
    duration = max(1, int(round(distance / speed * 60)))

    return {"distance_km": distance, "transport": transport, "duration_minutes": duration}
