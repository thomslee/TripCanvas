# -*- coding: utf-8 -*-
import paramiko

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd, timeout=60):
    _, o, e = cli.exec_command(cmd, timeout=timeout)
    return o.read().decode('utf-8', errors='replace')

# 检查重庆相关 POI 的经纬度
print("=== 重庆 POI 经纬度 ===")
print(run("""docker exec news-mysql mysql -uroot -p123456 -e "
SELECT id, name, poi_type, city, lat, lng, source 
FROM trip_canvas.pois 
WHERE name LIKE '%洪崖洞%' OR name LIKE '%解放碑%' OR name LIKE '%江北机场%' OR name LIKE '%威斯汀%'
ORDER BY id;
" 2>&1 | grep -v Warning"""))

# 检查节点的经纬度
print("\n=== 重庆节点经纬度 ===")
print(run("""docker exec news-mysql mysql -uroot -p123456 -e "
SELECT n.id, n.name, n.lat, n.lng, n.poi_id, p.name as poi_name, p.lat as poi_lat, p.lng as poi_lng
FROM trip_canvas.itinerary_nodes n
LEFT JOIN trip_canvas.pois p ON n.poi_id = p.id
WHERE n.trip_id = 5 AND (n.name LIKE '%洪崖洞%' OR n.name LIKE '%解放碑%' OR n.name LIKE '%江北机场%' OR n.name LIKE '%威斯汀%');
" 2>&1 | grep -v Warning"""))

cli.close()
