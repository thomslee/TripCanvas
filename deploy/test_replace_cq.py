# -*- coding: utf-8 -*-
import paramiko, json

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd, timeout=120):
    _, o, e = cli.exec_command(cmd, timeout=timeout)
    return o.read().decode('utf-8', errors='replace')

token = json.loads(run("""curl -s -X POST http://127.0.0.1:8002/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'"""))['token']
h = f"-H 'Authorization: Bearer {token}'"

# 先看当前 ai 节点
print("=== 替换前 ai 节点 ===")
tl = json.loads(run(f"curl -s http://127.0.0.1:8002/api/trips/5/timeline {h}"))
for day in tl['days']:
    for n in day['nodes']:
        poi = n.get('poi') or {}
        if poi.get('source') == 'ai':
            print(f"  D{day['day_no']}({day.get('city')}): {n['name']} type={n['node_type']}")

# 执行一键替换
print("\n=== 执行一键替换 ===")
r = run(f"curl -s -X POST http://127.0.0.1:8002/api/trips/5/auto-replace-pois {h}", timeout=90)
print(r[:500])

# 替换后查看
print("\n=== 替换后重庆节点 ===")
tl = json.loads(run(f"curl -s http://127.0.0.1:8002/api/trips/5/timeline {h}"))
for day in tl['days']:
    if day.get('city') == '重庆':
        print(f"  D{day['day_no']}:")
        for n in day['nodes']:
            poi = n.get('poi') or {}
            print(f"    {n['name']} | source={poi.get('source')} | poi_name={poi.get('name')}")

cli.close()
