# -*- coding: utf-8 -*-
import paramiko

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd, timeout=120):
    _, o, e = cli.exec_command(cmd, timeout=timeout)
    return o.read().decode('utf-8', errors='replace')

script = '''
import sys
sys.path.insert(0, "/app")
from app.database import SessionLocal
from app.models import Poi, ItineraryNode
from app.services.amap_service import search_pois

db = SessionLocal()

# 1. 实时搜索重庆威斯汀酒店
print("=== 高德实时搜索：重庆威斯汀酒店 ===")
results = search_pois(db, keyword="威斯汀酒店", city="重庆", limit=10)
for p in results[:5]:
    print(f"  id={p.id} name={p.name} type={p.poi_type} lat={p.lat} lng={p.lng} source={p.source}")

# 2. 实时搜索重庆解放碑
print("\\n=== 高德实时搜索：重庆解放碑步行街 ===")
results2 = search_pois(db, keyword="解放碑步行街", city="重庆", limit=10)
for p in results2[:5]:
    print(f"  id={p.id} name={p.name} type={p.poi_type} lat={p.lat} lng={p.lng} source={p.source}")

# 3. 替换节点
westin = next((p for p in results if p.poi_type == "hotel" and p.lat), None)
jiefangbei = next((p for p in results2 if p.poi_type == "attraction" and p.lat), None)

if westin:
    print(f"\\n替换威斯汀酒店为: {westin.name} (id={westin.id})")
    for nid in [58, 61, 62]:
        node = db.get(ItineraryNode, nid)
        if node:
            node.poi_id = westin.id
            print(f"  节点 {nid} 已更新")

if jiefangbei:
    print(f"\\n替换解放碑步行街为: {jiefangbei.name} (id={jiefangbei.id})")
    node = db.get(ItineraryNode, 59)
    if node:
        node.poi_id = jiefangbei.id
        print(f"  节点 59 已更新")

db.commit()

# 4. 重新计算所有边
print("\\n=== 重新计算所有边 ===")
from app.services import distance_service
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
print("\\n=== trip 5 边验证 ===")
from app.models import TripDay
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
print("\\n完成！")
'''
sftp = cli.open_sftp()
with sftp.file("/tmp/fix_and_recalc.py", "w") as f:
    f.write(script)
sftp.close()
print(run("docker cp /tmp/fix_and_recalc.py trip-backend:/tmp/fix_and_recalc.py && docker exec trip-backend python /tmp/fix_and_recalc.py"))

cli.close()
