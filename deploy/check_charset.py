# -*- coding: utf-8 -*-
import paramiko

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd):
    _, o, e = cli.exec_command(cmd, timeout=30)
    return o.read().decode() + e.read().decode()

# 查数据库和表字符集
print("=== 数据库字符集 ===")
print(run("docker exec news-mysql mysql -uroot -p123456 -e \"SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='trip_canvas';\" 2>/dev/null"))

print("=== pois 表字符集 ===")
print(run("docker exec news-mysql mysql -uroot -p123456 -e \"SELECT TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA='trip_canvas' AND TABLE_NAME='pois';\" 2>/dev/null"))

print("=== 前10个POI ===")
print(run("docker exec news-mysql mysql -uroot -p123456 -e \"SELECT id, name, city, source FROM trip_canvas.pois LIMIT 10;\" 2>/dev/null"))

print("=== MySQL 字符集变量 ===")
print(run("docker exec news-mysql mysql -uroot -p123456 -e \"SHOW VARIABLES LIKE 'character%'; SHOW VARIABLES LIKE 'collation%';\" 2>/dev/null"))

cli.close()
