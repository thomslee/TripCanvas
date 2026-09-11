# -*- coding: utf-8 -*-
import paramiko, json

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd):
    _, o, e = cli.exec_command(cmd, timeout=30)
    return o.read().decode() + e.read().decode()

# 登录
login_cmd = """curl -s -X POST http://127.0.0.1:8002/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'"""
token = json.loads(run(login_cmd))['token']
print("登录成功")

# 批量更新设置
body = json.dumps({
    "llm_base_url": "https://api.deepseek.com",
    "llm_model": "deepseek-chat",
    "llm_api_key": "sk-b6d3550501e44937a131d69d5516f9cb",
    "amap_key": "f724edc8e022ce60d793f10562cecea3",
    "weather_provider": "open-meteo",
})
cmd = f"""curl -s -X PUT http://127.0.0.1:8002/api/settings -H 'Content-Type: application/json' -H 'Authorization: Bearer {token}' -d '{body}'"""
r = run(cmd)
print("更新结果:", r[:300])

# 验证
r = run(f"curl -s http://127.0.0.1:8002/api/settings -H 'Authorization: Bearer {token}'")
print("\n当前配置:", r)

cli.close()
