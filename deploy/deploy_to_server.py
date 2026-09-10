# -*- coding: utf-8 -*-
"""途迹 TripCanvas 一键部署到腾讯云服务器"""
import os
import sys
import tarfile
import tempfile
import time
import paramiko

HOST = "82.156.177.145"
USER = "ubuntu"
PASSWORD = "Thomslee0529"
LOCAL = r"E:\travel"

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

def put(cli, local_path, remote_path):
    sftp = cli.open_sftp()
    # sftp 不识别 ~，转为绝对路径
    if remote_path.startswith("~/"):
        remote_path = "/home/ubuntu/" + remote_path[2:]
    print(f"上传 {local_path} -> {remote_path}")
    sftp.put(local_path, remote_path)
    sftp.close()

def make_tar(source_dir, output_tar, exclude_dirs=None, exclude_patterns=None):
    """打包目录为 tar.gz"""
    import fnmatch
    exclude_dirs = exclude_dirs or []
    exclude_patterns = exclude_patterns or []
    with tarfile.open(output_tar, "w:gz") as tar:
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for f in files:
                if any(fnmatch.fnmatch(f, pat) for pat in exclude_patterns):
                    continue
                full = os.path.join(root, f)
                arcname = os.path.relpath(full, os.path.dirname(source_dir))
                tar.add(full, arcname=arcname)
    print(f"打包完成: {output_tar} ({os.path.getsize(output_tar)//1024} KB)")

def main():
    cli = connect()
    print("=== 已连接服务器 ===")

    # 1. 创建目录
    run(cli, "mkdir -p ~/trip/backend")
    run(cli, "sudo mkdir -p /var/www/trip/releases")
    run(cli, "sudo chown ubuntu:ubuntu /var/www/trip")

    # 2. 打包后端
    backend_tar = os.path.join(tempfile.gettempdir(), "trip-backend.tar.gz")
    make_tar(
        os.path.join(LOCAL, "backend"),
        backend_tar,
        exclude_dirs=[".venv", "__pycache__", ".pytest_cache"],
        exclude_patterns=[".env", "test_*.py"]
    )
    put(cli, backend_tar, "/tmp/trip-backend.tar.gz")
    run(cli, "cd ~/trip && tar xzf /tmp/trip-backend.tar.gz")

    # 3. 上传 docker-compose.yml
    put(cli, os.path.join(LOCAL, "docker-compose.yml"), "~/trip/docker-compose.yml")

    # 4. 上传 .env（服务器用）
    env_content = "DB_PASSWORD=123456\n"
    sftp = cli.open_sftp()
    with sftp.file("/home/ubuntu/trip/.env", "w") as f:
        f.write(env_content)
    sftp.close()

    # 5. 打包前端 dist
    dist_tar = os.path.join(tempfile.gettempdir(), "trip-dist.tar.gz")
    make_tar(os.path.join(LOCAL, "frontend", "dist"), dist_tar)
    put(cli, dist_tar, "/tmp/trip-dist.tar.gz")
    run(cli, "mkdir -p /var/www/trip/releases/v1.0.0 && cd /var/www/trip/releases/v1.0.0 && tar xzf /tmp/trip-dist.tar.gz --strip-components=1")

    # 6. 切换 nginx 前端链接
    run(cli, "ln -sfn /var/www/trip/releases/v1.0.0 /var/www/trip/current")

    # 7. 上传 nginx 配置
    put(cli, os.path.join(LOCAL, "deploy", "trip-nginx.conf"), "/tmp/trip-nginx.conf")
    run(cli, "sudo cp /tmp/trip-nginx.conf /etc/nginx/sites-available/trip")
    run(cli, "sudo ln -sf /etc/nginx/sites-available/trip /etc/nginx/sites-enabled/trip")
    run(cli, "sudo nginx -t && sudo systemctl reload nginx")

    # 8. 创建数据库
    run(cli, "docker exec news-mysql mysql -uroot -p123456 -e \"CREATE DATABASE IF NOT EXISTS trip_canvas CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\" 2>/dev/null || true")

    # 9. 构建后端镜像
    print("=== 构建后端镜像（可能需要几分钟）===")
    run(cli, "cd ~/trip && nohup docker compose build backend > /tmp/trip-build.log 2>&1 & echo OK")
    # 等待构建完成
    for i in range(60):
        time.sleep(10)
        ps = run(cli, "ps aux | grep -c '[d]ocker build'")
        if ps.strip() == "0":
            break
        print(f"  构建中... ({i*10}s)")
    run(cli, "tail -n 5 /tmp/trip-build.log")

    # 10. 初始化数据库
    run(cli, "cd ~/trip && docker compose run --rm backend python init_db.py || echo 'init done'")

    # 11. 启动后端
    run(cli, "cd ~/trip && docker compose up -d backend")
    time.sleep(3)
    run(cli, "docker ps --format '{{.Names}} {{.Status}}' | grep trip")

    # 12. 健康检查
    time.sleep(2)
    run(cli, "curl -s http://127.0.0.1:8002/api/health")

    # 13. 验证前端
    run(cli, "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8081/")

    print("\n=== 部署完成 ===")
    print("访问地址: http://82.156.177.145:8081")
    print("默认管理员: admin / admin123")

    cli.close()

if __name__ == "__main__":
    main()
