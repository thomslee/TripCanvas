# -*- coding: utf-8 -*-
import paramiko

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd, timeout=60):
    _, o, e = cli.exec_command(cmd, timeout=timeout)
    return o.read().decode('utf-8', errors='replace')

# 直接用 Python 在容器内查询
script = '''
import sys
sys.path.insert(0, "/app")
from app.database import SessionLocal
from app.models import Poi, ItineraryNode

db = SessionLocal()
print("=== 重庆 POI ===")
pois = db.query(Poi).filter(Poi.city == "重庆").all()
for p in pois[:20]:
    print(f"  id={p.id} name={p.name} type={p.poi_type} lat={p.lat} lng={p.lng} source={p.source}")

print("\\n=== trip 5 节点 ===")
nodes = db.query(ItineraryNode).filter(ItineraryNode.trip_id == 5).all()
for n in nodes:
    poi = db.query(Poi).filter(Poi.id == n.poi_id).first() if n.poi_id else None
    poi_info = f"poi={poi.name} lat={poi.lat} lng={poi.lng}" if poi else "poi=None"
    print(f"  id={n.id} name={n.name} node_lat={n.lat} node_lng={n.lng} {poi_info}")

db.close()
'''
sftp = cli.open_sftp()
with sftp.file("/tmp/check_coords.py", "w") as f:
    f.write(script)
sftp.close()
print(run("docker cp /tmp/check_coords.py trip-backend:/tmp/check_coords.py && docker exec trip-backend python /tmp/check_coords.py"))

cli.close()
