# -*- coding: utf-8 -*-
import paramiko
cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)
cmds = [
    "ps aux | grep docker | grep -v grep | head -5",
    "echo '---build log tail---'",
    "tail -n 3 /tmp/trip-build.log",
    "echo '---docker images---'",
    "docker images | grep trip",
]
for cmd in cmds:
    _, o, e = cli.exec_command(cmd)
    print(o.read().decode())
cli.close()
