# -*- coding: utf-8 -*-
"""续跑：前端上传 + 后端构建启动"""
import os
import time
import paramiko

HOST = "82.156.177.145"
USER = "ubuntu"
PASSWORD = "Thomslee0529"

def connect():
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(HOST, port=22, username=USER, password=PASSWORD, timeout=30)
    return cli

def run(cli, cmd, timeout=300):
    print(f"$ {cmd}")
    _, out, err = cli.exec_command(cmd, timeout=timeout)
    o = out.read().decode("utf-8", "replace")
    e = err.read().decode("utf-8", "replace")
    if o.strip():
        print(o.strip())
    if e.strip():
        print("ERR:", e.strip())
    return o.strip()

def main():
    cli = connect()
    print("=== 已连接 ===")

    # 1. 修复前端目录权限并上传
    run(cli, "sudo mkdir -p /var/www/trip/releases/v1.0.0 && sudo chown -R ubuntu:ubuntu /var/www/trip")
    run(cli, "cd /var/www/trip/releases/v1.0.0 && tar xzf /tmp/trip-dist.tar.gz --strip-components=1")
    run(cli, "ln -sfn /var/www/trip/releases/v1.0.0 /var/www/trip/current")
    run(cli, "ls /var/www/trip/current/")

    # 2. 构建后端镜像（用 setsid 避免阻塞）
    print("=== 构建后端镜像 ===")
    run(cli, "cd ~/trip && setsid docker compose build backend > /tmp/trip-build.log 2>&1 < /dev/null &")
    # 等待构建完成
    for i in range(80):
        time.sleep(10)
        ps = run(cli, "ps aux | grep -c '[d]ocker build'")
        if ps.strip() == "0":
            print("构建进程结束")
            break
        if i % 3 == 0:
            print(f"  构建中... ({i*10}s)")
    run(cli, "tail -n 8 /tmp/trip-build.log")

    # 3. 初始化数据库
    print("=== 初始化数据库 ===")
    run(cli, "cd ~/trip && docker compose run --rm backend python init_db.py 2>&1 | tail -5")

    # 4. 启动后端
    print("=== 启动后端 ===")
    run(cli, "cd ~/trip && docker compose up -d backend")
    time.sleep(5)
    run(cli, "docker ps --format '{{.Names}} {{.Status}}' | grep trip")

    # 5. 健康检查
    time.sleep(3)
    run(cli, "curl -s http://127.0.0.1:8002/api/health")
    run(cli, "curl -s -o /dev/null -w '前端HTTP状态: %{http_code}\\n' http://127.0.0.1:8081/")

    # 6. 后端日志
    run(cli, "docker logs trip-backend --tail 10 2>&1")

    print("\n=== 部署完成 ===")
    print("访问: http://82.156.177.145:8081")
    print("管理员: admin / admin123")
    cli.close()

if __name__ == "__main__":
    main()
