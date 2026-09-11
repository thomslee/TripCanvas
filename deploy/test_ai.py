# -*- coding: utf-8 -*-
import paramiko, json, time

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd, timeout=120):
    _, o, e = cli.exec_command(cmd, timeout=timeout)
    return o.read().decode() + e.read().decode()

# 登录
token = json.loads(run("""curl -s -X POST http://127.0.0.1:8002/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'"""))['token']
h = f"-H 'Authorization: Bearer {token}' -H 'Content-Type: application/json'"

# 创建测试行程
body = json.dumps({"title":"部署测试-大理","dest_city":"大理","depart_city":"北京","depart_date":"2026-10-01","return_date":"2026-10-03","total_days":3,"depart_transport":"plane","arrive_station":"大理凤仪机场"})
trip = json.loads(run(f"curl -s -X POST http://127.0.0.1:8002/api/trips {h} -d '{body}'"))
tid = trip['trip']['id']
print(f"创建行程 id={tid}")

# AI 规划
print("AI 规划中...")
r = run(f"curl -s -X POST http://127.0.0.1:8002/api/trips/{tid}/ai-plan {h}", timeout=90)
print("AI规划结果:", r[:300])

# 查看节点
tl = json.loads(run(f"curl -s http://127.0.0.1:8002/api/trips/{tid}/timeline {h}"))
for day in tl['days']:
    print(f"  D{day['day_no']}: {[(n['name'], n['node_type']) for n in day['nodes']]}")

cli.close()
