# -*- coding: utf-8 -*-
import paramiko, time, json

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd, timeout=300):
    _, o, e = cli.exec_command(cmd, timeout=timeout)
    return o.read().decode('utf-8', errors='replace') + e.read().decode('utf-8', errors='replace')

# 1. 数据库迁移：加 distance_km 字段（如果不存在）
print("=== 数据库迁移 ===")
print(run("docker exec news-mysql mysql -uroot -p123456 -e \"ALTER TABLE trip_canvas.itinerary_edges ADD COLUMN IF NOT EXISTS distance_km DECIMAL(6,2) DEFAULT NULL AFTER duration_minutes;\" 2>&1 | grep -v Warning"))
print(run("docker exec news-mysql mysql -uroot -p123456 -e \"DESCRIBE trip_canvas.itinerary_edges;\" 2>&1 | grep -v Warning"))

# 2. 上传修改的文件
print("\n=== 上传文件 ===")
sftp = cli.open_sftp()
files = [
    (r"E:\travel\backend\app\models\itinerary.py", "/home/ubuntu/trip/backend/app/models/itinerary.py"),
    (r"E:\travel\backend\app\services\distance_service.py", "/home/ubuntu/trip/backend/app/services/distance_service.py"),
    (r"E:\travel\backend\app\services\seed_planner.py", "/home/ubuntu/trip/backend/app/services/seed_planner.py"),
    (r"E:\travel\backend\app\routers\itinerary.py", "/home/ubuntu/trip/backend/app/routers/itinerary.py"),
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
    if i % 3 == 0:
        print(f"  构建中... ({i*10}s)")
print(run("tail -n 3 /tmp/trip-rebuild.log"))

# 4. 重启
run("cd ~/trip && docker compose up -d backend")
time.sleep(5)
print(run("docker ps --format '{{.Names}} {{.Status}}' | grep trip"))
print("健康检查:", run("curl -s http://127.0.0.1:8002/api/health"))

cli.close()
print("\n完成！")
