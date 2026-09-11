# -*- coding: utf-8 -*-
import paramiko, time

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd, timeout=300):
    _, o, e = cli.exec_command(cmd, timeout=timeout)
    return o.read().decode('utf-8', errors='replace') + e.read().decode('utf-8', errors='replace')

sftp = cli.open_sftp()
sftp.put(r"E:\travel\backend\app\services\weather_service.py", "/home/ubuntu/trip/backend/app/services/weather_service.py")
sftp.close()
print("weather_service.py 已上传")

print("重新构建...")
run("cd ~/trip && setsid docker compose build backend > /tmp/trip-rebuild.log 2>&1 < /dev/null &")
for i in range(60):
    time.sleep(10)
    _, o, _ = cli.exec_command("ps aux | grep 'docker compose build' | grep -v grep | wc -l")
    if o.read().decode().strip() == "0":
        print("构建完成")
        break
    if i % 3 == 0:
        print(f"  构建中... ({i*10}s)")
print(run("tail -n 3 /tmp/trip-rebuild.log"))

run("cd ~/trip && docker compose up -d backend")
time.sleep(5)
print(run("docker ps --format '{{.Names}} {{.Status}}' | grep trip"))
print("健康检查:", run("curl -s http://127.0.0.1:8002/api/health"))

# 验证天气返回3天
print("\n天气验证:")
r = run("curl -s 'http://127.0.0.1:8002/api/weather?city=%E9%87%8D%E5%BA%86'")
import json
d = json.loads(r)
print(f"  forecast天数: {len(d.get('forecast', []))}")
for f in d.get('forecast', []):
    print(f"    {f['date']}: {f['desc']} {f['temp_min']}~{f['temp_max']}°C")

cli.close()
