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

# 1. 找到李子坝轻轨站的节点 id
tl = json.loads(run(f"curl -s http://127.0.0.1:8002/api/trips/5/timeline {h}"))
node_id = None
for day in tl['days']:
    for n in day['nodes']:
        if '李子坝' in n['name']:
            node_id = n['id']
            print(f"找到节点: id={n['id']} name={n['name']} current_poi={n.get('poi',{}).get('name')}")

# 2. 搜索高德"李子坝轻轨站"（重庆）
search_result = json.loads(run(f"curl -s 'http://127.0.0.1:8002/api/pois/search-amap?q=%E6%9D%8E%E5%AD%90%E5%9D%9D%E8%BD%BB%E8%BD%A8%E7%AB%99&city=%E9%87%8D%E5%BA%86&limit=5' {h}"))
if isinstance(search_result, dict):
    search_result = search_result.get('results', [])
print("\n高德搜索结果:")
for p in search_result[:5]:
    print(f"  id={p['id']} name={p['name']} type={p['poi_type']} addr={p.get('address')}")

# 3. 取第一个 attraction 类型的结果替换
target_poi = next((p for p in search_result if p.get('poi_type') == 'attraction'), None)
if target_poi and node_id:
    print(f"\n替换为: {target_poi['name']} (id={target_poi['id']})")
    body = json.dumps({"poi_id": target_poi['id']})
    r = run(f"curl -s -X PATCH http://127.0.0.1:8002/api/nodes/{node_id} {h} -d '{body}'")
    print("替换结果:", r[:200])

# 4. 验证
tl = json.loads(run(f"curl -s http://127.0.0.1:8002/api/trips/5/timeline {h}"))
for day in tl['days']:
    for n in day['nodes']:
        if '李子坝' in n['name']:
            poi = n.get('poi') or {}
            print(f"\n验证: {n['name']} -> {poi.get('name')} (source={poi.get('source')}, addr={poi.get('address')})")

cli.close()
