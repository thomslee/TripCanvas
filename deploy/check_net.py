# -*- coding: utf-8 -*-
import paramiko
cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)
_, o, _ = cli.exec_command("docker inspect news-mysql --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'")
print("news-mysql网络:", o.read().decode())
_, o, _ = cli.exec_command("docker network ls")
print("所有网络:", o.read().decode())
cli.close()
