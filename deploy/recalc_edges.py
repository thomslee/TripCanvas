# -*- coding: utf-8 -*-
import paramiko, json

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd, timeout=120):
    _, o, e = cli.exec_command(cmd, timeout=timeout)
    return o.read().decode('utf-8', errors='replace')

# 1. 加 distance_km 字段
print("=== 加字段 ===")
print(run("docker exec news-mysql mysql -uroot -p123456 -e \"ALTER TABLE trip_canvas.itinerary_edges ADD COLUMN distance_km DECIMAL(6,2) DEFAULT NULL AFTER duration_minutes;\" 2>&1 | grep -v Warning"))

# 2. 验证
print(run("docker exec news-mysql mysql -uroot -p123456 -e \"DESCRIBE trip_canvas.itinerary_edges;\" 2>&1 | grep -v Warning"))

# 3. 登录获取 token
token = json.loads(run("""curl -s -X POST http://127.0.0.1:8002/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'"""))['token']
h = f"-H 'Authorization: Bearer {token}'"

# 4. 对每个行程，触发边重建（通过调整节点顺序触发 _rebuild_day_edges）
# 更简单的方式：直接调用后端的一个端点，或者用 Python 在容器内执行
# 这里用 docker exec 运行 Python 脚本重新计算所有边
print("\n=== 重新计算所有边的距离和交通方式 ===")
script = '''
import sys
sys.path.insert(0, "/app")
from app.database import SessionLocal
from app.models import ItineraryEdge, ItineraryNode
from app.services import distance_service

db = SessionLocal()
edges = db.query(ItineraryEdge).all()
updated = 0
for edge in edges:
    from_node = db.get(ItineraryNode, edge.from_node_id)
    to_node = db.get(ItineraryNode, edge.to_node_id)
    if not from_node or not to_node:
        continue
    t = distance_service.calc_transport(db, from_node, to_node)
    edge.distance_km = t["distance_km"]
    # 只对默认步行边自动切换交通方式，保留用户已手动设置的
    if edge.transport == "walk" and edge.duration_minutes in (15, 30):
        edge.transport = t["transport"]
        edge.duration_minutes = t["duration_minutes"]
    updated += 1
db.commit()
print(f"更新了 {updated} 条边")

# 统计
walk_count = db.query(ItineraryEdge).filter(ItineraryEdge.transport == "walk").count()
taxi_count = db.query(ItineraryEdge).filter(ItineraryEdge.transport == "taxi").count()
with_dist = db.query(ItineraryEdge).filter(ItineraryEdge.distance_km != None).count()
print(f"步行边: {walk_count}, 打车边: {taxi_count}, 有距离: {with_dist}")
db.close()
'''
# 写入临时文件并执行
sftp = cli.open_sftp()
with sftp.file("/tmp/recalc_edges.py", "w") as f:
    f.write(script)
sftp.close()
print(run("docker cp /tmp/recalc_edges.py trip-backend:/tmp/recalc_edges.py && docker exec trip-backend python /tmp/recalc_edges.py"))

# 5. 验证南昌+重庆行程的边
print("\n=== 验证 trip 5 的边 ===")
tl = json.loads(run(f"curl -s http://127.0.0.1:8002/api/trips/5/timeline {h}"))
for day in tl['days']:
    print(f"  D{day['day_no']} ({day.get('city')}):")
    for e in day.get('edges', []):
        from_name = next((n['name'] for n in day['nodes'] if n['id'] == e['from_node_id']), '?')
        to_name = next((n['name'] for n in day['nodes'] if n['id'] == e['to_node_id']), '?')
        dist = f"{e['distance_km']}km" if e.get('distance_km') else "?"
        print(f"    {from_name} -> {to_name}: {e['transport']} {e['duration_minutes']}min {dist}")

cli.close()
