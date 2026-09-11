# -*- coding: utf-8 -*-
import paramiko, json

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd, timeout=60):
    _, o, e = cli.exec_command(cmd, timeout=timeout)
    return o.read().decode('utf-8', errors='replace')

token = json.loads(run("""curl -s -X POST http://127.0.0.1:8002/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'"""))['token']
h = f"-H 'Authorization: Bearer {token}' -H 'Content-Type: application/json'"

# 1. 搜索重庆的威斯汀酒店
print("=== 搜索重庆威斯汀酒店 ===")
r = json.loads(run(f"curl -s 'http://127.0.0.1:8002/api/pois/search-amap?q=%E5%A8%81%E6%96%AF%E6%B1%80%E9%85%92%E5%BA%97&city=%E9%87%8D%E5%BA%86&limit=5' {h}"))
if isinstance(r, dict): r = r.get('results', [])
for p in r[:5]:
    print(f"  id={p['id']} name={p['name']} lat={p.get('lat')} lng={p.get('lng')}")

# 2. 搜索重庆解放碑步行街
print("\n=== 搜索重庆解放碑步行街 ===")
r2 = json.loads(run(f"curl -s 'http://127.0.0.1:8002/api/pois/search-amap?q=%E8%A7%A3%E6%94%BE%E7%A2%91%E6%AD%A5%E8%A1%8C%E8%A1%97&city=%E9%87%8D%E5%BA%86&limit=5' {h}"))
if isinstance(r2, dict): r2 = r2.get('results', [])
for p in r2[:5]:
    print(f"  id={p['id']} name={p['name']} lat={p.get('lat')} lng={p.get('lng')}")

# 3. 替换节点 58, 61, 62（重庆解放碑威斯汀酒店）和节点 59（解放碑步行街）
westin = next((p for p in r if p.get('poi_type') == 'hotel'), None)
jiefangbei = next((p for p in r2 if p.get('poi_type') == 'attraction'), None)

if westin:
    print(f"\n替换威斯汀酒店为: {westin['name']} (id={westin['id']})")
    for nid in [58, 61, 62]:
        body = json.dumps({"poi_id": westin['id']})
        print(run(f"curl -s -X PATCH http://127.0.0.1:8002/api/nodes/{nid} {h} -d '{body}'")[:100])

if jiefangbei:
    print(f"\n替换解放碑步行街为: {jiefangbei['name']} (id={jiefangbei['id']})")
    body = json.dumps({"poi_id": jiefangbei['id']})
    print(run(f"curl -s -X PATCH http://127.0.0.1:8002/api/nodes/59 {h} -d '{body}'")[:100])

cli.close()
