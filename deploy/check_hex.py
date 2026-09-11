# -*- coding: utf-8 -*-
import paramiko

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd):
    _, o, e = cli.exec_command(cmd, timeout=30)
    return o.read().decode('utf-8', errors='replace') + e.read().decode('utf-8', errors='replace')

# 用 hex 查看实际存储
print("=== POI id=18 hex ===")
print(run("docker exec news-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 -e \"SELECT id, HEX(name), HEX(city), source FROM trip_canvas.pois WHERE id=18;\" 2>/dev/null"))

print("=== 前5个POI (hex) ===")
print(run("docker exec news-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 -e \"SELECT id, HEX(name), source FROM trip_canvas.pois LIMIT 5;\" 2>/dev/null"))

print("=== MySQL connection charset ===")
print(run("docker exec news-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 -e \"SHOW VARIABLES LIKE 'character_set_client'; SHOW VARIABLES LIKE 'character_set_connection';\" 2>/dev/null"))

cli.close()
