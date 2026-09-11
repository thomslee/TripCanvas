# -*- coding: utf-8 -*-
import paramiko, time, json

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd, timeout=300):
    _, o, e = cli.exec_command(cmd, timeout=timeout)
    return o.read().decode('utf-8', errors='replace') + e.read().decode('utf-8', errors='replace')

# 1. 数据库迁移
print("=== 数据库迁移 ===")
print(run("docker exec news-mysql mysql -uroot -p123456 -e \"ALTER TABLE trip_canvas.pois ADD COLUMN phone VARCHAR(64) DEFAULT NULL AFTER open_hours;\" 2>&1 | grep -v Warning"))

# 2. 上传文件
print("\n=== 上传文件 ===")
sftp = cli.open_sftp()
files = [
    (r"E:\travel\backend\app\models\poi.py", "/home/ubuntu/trip/backend/app/models/poi.py"),
    (r"E:\travel\backend\app\schemas\itinerary.py", "/home/ubuntu/trip/backend/app/schemas/itinerary.py"),
    (r"E:\travel\backend\app\services\amap_service.py", "/home/ubuntu/trip/backend/app/services/amap_service.py"),
]
for local, remote in files:
    sftp.put(local, remote)
    print(f"  上传: {local.split(chr(92))[-1]}")
sftp.close()

# 3. 重新构建
print("\n=== 重新构建 ===")
run("cd ~/trip && setsid docker compose build backend > /tmp/trip-rebuild.log 2>&1 < /dev/null &")
for i in range(60):
    time.sleep(10)
    _, o, _ = cli.exec_command("ps aux | grep 'docker compose build' | grep -v grep | wc -l")
    if o.read().decode().strip() == "0":
        print("构建完成")
        break
print(run("tail -n 2 /tmp/trip-rebuild.log"))
run("cd ~/trip && docker compose up -d backend")
time.sleep(5)
print(run("docker ps --format '{{.Names}} {{.Status}}' | grep trip"))

# 4. 补充已有 POI 的电话信息（重新搜索高德）
print("\n=== 补充已有 POI 电话 ===")
script = '''
import sys
sys.path.insert(0, "/app")
from app.database import SessionLocal
from app.models import Poi
from app.services.amap_service import search_pois

db = SessionLocal()
# 对没有电话的 gaode POI，重新搜索高德补充电话
pois = db.query(Poi).filter(Poi.source == "gaode", Poi.phone == None).limit(30).all()
updated = 0
for p in pois:
    try:
        results = search_pois(db, keyword=p.name, city=p.city, limit=5)
        for r in results:
            if r.name == p.name and r.phone:
                p.phone = r.phone
                updated += 1
                break
    except Exception as e:
        print(f"  跳过 {p.name}: {e}")
db.commit()
print(f"补充了 {updated} 个 POI 的电话")

# 验证
samples = db.query(Poi).filter(Poi.phone != None).limit(5).all()
for p in samples:
    print(f"  {p.name}: {p.phone}")
db.close()
'''
sftp = cli.open_sftp()
with sftp.file("/tmp/fill_phone.py", "w") as f:
    f.write(script)
sftp.close()
print(run("docker cp /tmp/fill_phone.py trip-backend:/tmp/fill_phone.py && docker exec trip-backend python /tmp/fill_phone.py 2>&1"))

cli.close()
print("\n完成！")
