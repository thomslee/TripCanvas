# -*- coding: utf-8 -*-
import paramiko, json
cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

# 测试登录
cmd = """curl -s -X POST http://127.0.0.1:8002/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'"""
_, o, _ = cli.exec_command(cmd)
print("登录:", o.read().decode())

# 检查数据库表
_, o, _ = cli.exec_command("docker exec news-mysql mysql -uroot -p123456 -e 'SHOW TABLES FROM trip_canvas;' 2>/dev/null")
print("数据库表:", o.read().decode())

# 检查 news-mysql 端口映射
_, o, _ = cli.exec_command("docker port news-mysql")
print("news-mysql端口:", o.read().decode())

cli.close()
