# -*- coding: utf-8 -*-
import paramiko, json

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd):
    _, o, e = cli.exec_command(cmd, timeout=30)
    return o.read().decode() + e.read().decode()

# 查 poi_id=18 的详细信息
print("=== POI id=18 ===")
r = run("docker exec news-mysql mysql -uroot -p123456 -e \"SELECT id, name, poi_type, city, address, source, lat, lng FROM trip_canvas.pois WHERE id=18;\" 2>/dev/null")
print(r)

# 查所有含兵马俑的 POI
print("=== 所有含兵马俑的 POI ===")
r = run("docker exec news-mysql mysql -uroot -p123456 -e \"SELECT id, name, poi_type, source, address FROM trip_canvas.pois WHERE name LIKE '%兵马俑%';\" 2>/dev/null")
print(r)

# 在服务器上测试高德搜索
print("=== 服务器上高德搜索 ===")
r = run("curl -s 'https://restapi.amap.com/v3/place/text?keywords=%E7%A7%A6%E5%A7%8B%E7%9A%87%E5%85%B5%E9%A9%AC%E4%BF%91%E5%8D%9A%E7%89%A9%E9%A6%86&city=%E8%A5%BF%E5%AE%89&citylimit=true&offset=3&key=f724edc8e022ce60d793f10562cecea3'")
d = json.loads(r)
print(f"数量: {d.get('count')}")
for p in d.get('pois', [])[:3]:
    print(f"  {p.get('name')} | type={p.get('type')} | addr={p.get('address')}")

cli.close()
