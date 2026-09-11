# -*- coding: utf-8 -*-
import paramiko

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd, timeout=60):
    _, o, e = cli.exec_command(cmd, timeout=timeout)
    return o.read().decode('utf-8', errors='replace') + e.read().decode('utf-8', errors='replace')

# 检查容器内的 schemas 文件
print("=== 容器内 EdgeOut ===")
print(run("docker exec trip-backend grep -A 8 'class EdgeOut' /app/app/schemas/itinerary.py"))

# 检查数据库中的值
print("\n=== 数据库 edge 87 ===")
print(run("docker exec trip-backend python -c \"import sys; sys.path.insert(0,'/app'); from app.database import SessionLocal; from app.models import ItineraryEdge; db=SessionLocal(); e=db.get(ItineraryEdge,87); print(f'transport={e.transport} dur={e.duration_minutes} dist={e.distance_km}')\""))

cli.close()
