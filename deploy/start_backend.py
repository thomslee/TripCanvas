# -*- coding: utf-8 -*-
import paramiko, time
cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd, timeout=120):
    _, o, e = cli.exec_command(cmd, timeout=timeout)
    r = o.read().decode() + e.read().decode()
    print(f"$ {cmd}")
    print(r)
    return r

# 1. 初始化数据库
print("=== 初始化数据库 ===")
run("cd ~/trip && docker compose run --rm backend python init_db.py 2>&1 | tail -10")

# 2. 启动后端
print("=== 启动后端 ===")
run("cd ~/trip && docker compose up -d backend")
time.sleep(5)
run("docker ps --format '{{.Names}} {{.Status}}' | grep trip")

# 3. 健康检查
time.sleep(3)
print("=== 健康检查 ===")
run("curl -s http://127.0.0.1:8002/api/health")
run("curl -s -o /dev/null -w '前端HTTP: %{http_code}\\n' http://127.0.0.1:8081/")

# 4. 后端日志
print("=== 后端日志 ===")
run("docker logs trip-backend --tail 15 2>&1")

cli.close()
print("\n=== 部署完成！===")
print("访问: http://82.156.177.145:8081")
print("管理员: admin / admin123")
