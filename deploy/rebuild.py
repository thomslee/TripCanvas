# -*- coding: utf-8 -*-
import paramiko, time
cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd, timeout=120):
    _, o, e = cli.exec_command(cmd, timeout=timeout)
    print(o.read().decode(), e.read().decode())

# 杀掉旧构建
run("pkill -f 'docker compose build' 2>/dev/null; sleep 2; echo killed")

# 上传新 Dockerfile
sftp = cli.open_sftp()
sftp.put(r"E:\travel\backend\Dockerfile", "/home/ubuntu/trip/backend/Dockerfile")
sftp.close()
print("Dockerfile 已上传")

# 重新构建
run("cd ~/trip && setsid docker compose build backend > /tmp/trip-build2.log 2>&1 < /dev/null &")
print("构建已启动，等待...")

# 等待构建
for i in range(60):
    time.sleep(10)
    _, o, _ = cli.exec_command("ps aux | grep 'docker compose build' | grep -v grep | wc -l")
    cnt = o.read().decode().strip()
    if cnt == "0":
        print("构建完成")
        break
    if i % 3 == 0:
        print(f"  构建中... ({i*10}s)")

run("tail -n 10 /tmp/trip-build2.log")
cli.close()
