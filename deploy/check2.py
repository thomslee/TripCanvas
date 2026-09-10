# -*- coding: utf-8 -*-
import paramiko
cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)
_, o, _ = cli.exec_command("ps aux | grep 'docker compose build' | grep -v grep | wc -l")
print("构建进程数:", o.read().decode().strip())
_, o, _ = cli.exec_command("tail -n 10 /tmp/trip-build2.log")
print(o.read().decode())
_, o, _ = cli.exec_command("docker images | grep trip")
print("镜像:", o.read().decode())
cli.close()
