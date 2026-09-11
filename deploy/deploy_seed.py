# -*- coding: utf-8 -*-
import paramiko, time, json

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd, timeout=300):
    _, o, e = cli.exec_command(cmd, timeout=timeout)
    return o.read().decode('utf-8', errors='replace') + e.read().decode('utf-8', errors='replace')

sftp = cli.open_sftp()
sftp.put(r"E:\travel\backend\app\services\seed_planner.py", "/home/ubuntu/trip/backend/app/services/seed_planner.py")
sftp.close()
print("seed_planner.py 已上传")

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

# 验证
token = json.loads(run("""curl -s -X POST http://127.0.0.1:8002/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'"""))['token']
tl = json.loads(run(f"curl -s http://127.0.0.1:8002/api/trips/5/timeline -H 'Authorization: Bearer {token}'"))
print("\nAPI 验证（前3条边）:")
for day in tl['days'][:1]:
    for e in day.get('edges', [])[:3]:
        print(f"  {e['transport']} {e['duration_minutes']}min dist={e.get('distance_km')}km")

cli.close()
