# -*- coding: utf-8 -*-
import paramiko, json

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

def run(cmd):
    _, o, e = cli.exec_command(cmd, timeout=30)
    return o.read().decode('utf-8', errors='replace')

token = json.loads(run("""curl -s -X POST http://127.0.0.1:8002/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'"""))['token']
h = f"-H 'Authorization: Bearer {token}'"

tl = json.loads(run(f"curl -s http://127.0.0.1:8002/api/trips/3/timeline {h}"))
for day in tl['days']:
    print(f"\nD{day['day_no']} ({day.get('city')}):")
    for n in day['nodes']:
        poi = n.get('poi') or {}
        print(f"  {n['name']} | type={n['node_type']} | poi_source={poi.get('source')} | poi_name={poi.get('name')}")

cli.close()
