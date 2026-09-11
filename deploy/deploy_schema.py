# -*- coding: utf-8 -*-
import paramiko, time

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd, timeout=300):
    _, o, e = cli.exec_command(cmd, timeout=timeout)
    return o.read().decode('utf-8', errors='replace') + e.read().decode('utf-8', errors='replace')

# 上传 schemas
sftp = cli.open_sftp()
sftp.put(r"E:\travel\backend\app\schemas\itinerary.py", "/home/ubuntu/trip/backend/app/schemas/itinerary.py")
sftp.close()
print("schemas/itinerary.py 已上传")

# 重新构建
print("重新构建...")
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

# 验证 API 返回 distance_km
print("\nAPI 验证:")
import json
token = json.loads(run("""curl -s -X POST http://127.0.0.1:8002/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'"""))['token']
tl = json.loads(run(f"curl -s http://127.0.0.1:8002/api/trips/5/timeline -H 'Authorization: Bearer {token}'"))
for day in tl['days'][:1]:
    for e in day.get('edges', [])[:2]:
        print(f"  edge {e['id']}: transport={e['transport']} dur={e['duration_minutes']} dist={e.get('distance_km')}")

cli.close()
