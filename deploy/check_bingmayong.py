# -*- coding: utf-8 -*-
import paramiko, json

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd, timeout=60):
    _, o, e = cli.exec_command(cmd, timeout=timeout)
    return o.read().decode() + e.read().decode()

# 1. 查看所有行程，找含兵马俑的
token = json.loads(run("""curl -s -X POST http://127.0.0.1:8002/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'"""))['token']
h = f"-H 'Authorization: Bearer {token}'"

trips = json.loads(run(f"curl -s http://127.0.0.1:8002/api/trips {h}"))
for t in trips:
    print(f"trip {t['id']}: {t['title']} (dest={t.get('dest_city')})")

# 2. 找含兵马俑的行程节点
print("\n=== 搜索含兵马俑的节点 ===")
for t in trips:
    tid = t['id']
    tl = json.loads(run(f"curl -s http://127.0.0.1:8002/api/trips/{tid}/timeline {h}"))
    for day in tl.get('days', []):
        for n in day.get('nodes', []):
            if '兵马俑' in n['name'] or '始皇' in n['name']:
                poi = n.get('poi') or {}
                print(f"  trip {tid} D{day['day_no']}: {n['name']} type={n['node_type']} poi_source={poi.get('source')} poi_id={poi.get('id')}")

# 3. 直接测试高德搜索
print("\n=== 高德搜索 秦始皇兵马俑博物馆 (西安) ===")
import urllib.request
key = "f724edc8e022ce60d793f10562cecea3"
url = f"https://restapi.amap.com/v3/place/text?keywords=秦始皇兵马俑博物馆&city=西安&citylimit=true&offset=5&page=1&key={key}"
d = json.loads(urllib.request.urlopen(url, timeout=15).read().decode())
print(f"状态: {d.get('status')} 数量: {d.get('count')}")
for p in d.get('pois', [])[:5]:
    print(f"  {p.get('name')} | type={p.get('type')} | addr={p.get('address')}")

cli.close()
