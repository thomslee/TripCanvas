# -*- coding: utf-8 -*-
import paramiko

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd, timeout=120):
    _, o, e = cli.exec_command(cmd, timeout=timeout)
    return o.read().decode('utf-8', errors='replace') + e.read().decode('utf-8', errors='replace')

sftp = cli.open_sftp()
sftp.put(r"E:\travel\deploy\container_fix.py", "/tmp/container_fix.py")
sftp.close()
print(run("docker cp /tmp/container_fix.py trip-backend:/tmp/container_fix.py && docker exec trip-backend python /tmp/container_fix.py 2>&1"))

cli.close()
