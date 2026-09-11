# -*- coding: utf-8 -*-
import paramiko, os

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd, timeout=120):
    _, o, e = cli.exec_command(cmd, timeout=timeout)
    return o.read().decode('utf-8', errors='replace') + e.read().decode('utf-8', errors='replace')

# 创建新版本目录
version = "v1.1.0"
run(f"mkdir -p /var/www/trip/releases/{version}")

# 上传 dist 目录
sftp = cli.open_sftp()
local_dist = r"E:\travel\frontend\dist"
remote_base = f"/var/www/trip/releases/{version}"

def upload_dir(local, remote):
    for item in os.listdir(local):
        local_path = os.path.join(local, item)
        remote_path = f"{remote}/{item}"
        if os.path.isdir(local_path):
            run(f"mkdir -p {remote_path}")
            upload_dir(local_path, remote_path)
        else:
            sftp.put(local_path, remote_path)

upload_dir(local_dist, remote_base)
sftp.close()
print(f"前端已上传到 {remote_base}")

# 切换 current 链接
run(f"ln -sfn /var/www/trip/releases/{version} /var/www/trip/current")
print("current 链接已切换")

# 验证
print("\n验证:")
print(run(f"readlink /var/www/trip/current"))
print(run("curl -s http://127.0.0.1:8081/ | grep -o 'index-[^\"']*\\.js' | head -1"))

cli.close()
