# -*- coding: utf-8 -*-
import paramiko, time
cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd, timeout=120):
    _, o, e = cli.exec_command(cmd, timeout=timeout)
    r = o.read().decode() + e.read().decode()
    print(f"$ {cmd[:80]}")
    if r.strip():
        print(r.strip()[:500])
    return r

# 上传 docker-compose
sftp = cli.open_sftp()
sftp.put(r"E:\travel\docker-compose.yml", "/home/ubuntu/trip/docker-compose.yml")
sftp.close()
print("docker-compose.yml 已上传")

# 停掉旧容器
run("cd ~/trip && docker compose down")

# 初始化数据库（现在容器能访问 news-mysql 了）
print("=== 初始化数据库 ===")
run("cd ~/trip && docker compose run --rm backend python init_db.py 2>&1 | tail -5")

# 启动后端
print("=== 启动后端 ===")
run("cd ~/trip && docker compose up -d backend")
time.sleep(5)
run("docker ps --format '{{.Names}} {{.Status}}' | grep trip")

# 健康检查
time.sleep(3)
print("=== 健康检查 ===")
run("curl -s http://127.0.0.1:8002/api/health")

# 测试登录
print("=== 测试登录 ===")
run("""curl -s -X POST http://127.0.0.1:8002/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'""")

# 前端
run("curl -s -o /dev/null -w '前端HTTP: %{http_code}\\n' http://127.0.0.1:8081/")

cli.close()
print("\n=== 完成 ===")
