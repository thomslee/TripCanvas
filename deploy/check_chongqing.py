# -*- coding: utf-8 -*-
import paramiko, json

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd, timeout=60):
    _, o, e = cli.exec_command(cmd, timeout=timeout)
    return o.read().decode('utf-8', errors='replace')

token = json.loads(run("""curl -s -X POST http://127.0.0.1:8002/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'"""))['token']
h = f"-H 'Authorization: Bearer {token}'"

# 1. 列出所有行程
trips = json.loads(run(f"curl -s http://127.0.0.1:8002/api/trips {h}"))
print("=== 所有行程 ===")
for t in trips:
    print(f"  {t['id']}: {t['title']} dest={t.get('dest_city')} cities={[c['city'] for c in (t.get('dest_cities') or [])]}")

# 2. 找重庆相关行程
print("\n=== 重庆行程节点详情 ===")
for t in trips:
    if '重庆' in t.get('dest_city','') or any('重庆' in c['city'] for c in (t.get('dest_cities') or [])):
        tid = t['id']
        print(f"\n--- trip {tid}: {t['title']} (dest_city={t.get('dest_city')}) ---")
        tl = json.loads(run(f"curl -s http://127.0.0.1:8002/api/trips/{tid}/timeline {h}"))
        for day in tl.get('days', []):
            print(f"  D{day['day_no']} city={day.get('city')}:")
            for n in day.get('nodes', []):
                poi = n.get('poi') or {}
                print(f"    {n['name']} | type={n['node_type']} | poi_source={poi.get('source')} | poi_name={poi.get('name')}")

cli.close()
