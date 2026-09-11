import sys
sys.path.insert(0, "/app")
from app.database import SessionLocal
from app.models import Poi, ItineraryNode, ItineraryEdge, TripDay
from app.services.amap_service import search_pois
from app.services import distance_service

db = SessionLocal()

# 1. 实时搜索重庆威斯汀酒店
print("=== 高德实时搜索：重庆威斯汀酒店 ===")
results = search_pois(db, keyword="威斯汀酒店", city="重庆", limit=10)
for p in results[:5]:
    print(f"  id={p.id} name={p.name} type={p.poi_type} lat={p.lat} lng={p.lng} source={p.source}")

# 2. 实时搜索重庆解放碑
print("\n=== 高德实时搜索：重庆解放碑步行街 ===")
results2 = search_pois(db, keyword="解放碑步行街", city="重庆", limit=10)
for p in results2[:5]:
    print(f"  id={p.id} name={p.name} type={p.poi_type} lat={p.lat} lng={p.lng} source={p.source}")

# 3. 替换节点
westin = next((p for p in results if p.poi_type == "hotel" and p.lat and p.source == "gaode"), None)
jiefangbei = next((p for p in results2 if p.poi_type == "attraction" and p.lat and p.source == "gaode"), None)

if westin:
    print(f"\n替换威斯汀酒店为: {westin.name} (id={westin.id})")
    for nid in [58, 61, 62]:
        node = db.get(ItineraryNode, nid)
        if node:
            node.poi_id = westin.id
            print(f"  节点 {nid} 已更新")
else:
    print("\n未找到重庆威斯汀酒店")

if jiefangbei:
    print(f"\n替换解放碑步行街为: {jiefangbei.name} (id={jiefangbei.id})")
    node = db.get(ItineraryNode, 59)
    if node:
        node.poi_id = jiefangbei.id
        print(f"  节点 59 已更新")
else:
    print("\n未找到重庆解放碑步行街")

db.commit()

# 4. 重新计算所有边
print("\n=== 重新计算所有边 ===")
edges = db.query(ItineraryEdge).all()
for edge in edges:
    from_node = db.get(ItineraryNode, edge.from_node_id)
    to_node = db.get(ItineraryNode, edge.to_node_id)
    if not from_node or not to_node:
        continue
    t = distance_service.calc_transport(db, from_node, to_node)
    edge.distance_km = t["distance_km"]
    # 跨城边（距离>100km）用飞机
    if t["distance_km"] and t["distance_km"] > 100:
        edge.transport = "plane"
        edge.duration_minutes = 120
    elif edge.transport in ("walk", "taxi") or edge.duration_minutes in (15, 30):
        edge.transport = t["transport"]
        edge.duration_minutes = t["duration_minutes"]
db.commit()

# 5. 验证 trip 5 的边
print("\n=== trip 5 边验证 ===")
days = db.query(TripDay).filter(TripDay.trip_id == 5).order_by(TripDay.day_no).all()
for day in days:
    nodes = db.query(ItineraryNode).filter(ItineraryNode.day_id == day.id).order_by(ItineraryNode.sort_order).all()
    print(f"  D{day.day_no} ({day.city}):")
    for i in range(len(nodes)-1):
        a, b = nodes[i], nodes[i+1]
        edge = db.query(ItineraryEdge).filter(ItineraryEdge.from_node_id == a.id, ItineraryEdge.to_node_id == b.id).first()
        if edge:
            dist = f"{edge.distance_km}km" if edge.distance_km else "?"
            print(f"    {a.name} -> {b.name}: {edge.transport} {edge.duration_minutes}min {dist}")

db.close()
print("\n完成！")
