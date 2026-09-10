# -*- coding: utf-8 -*-
import sys, io, json, time, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
base = 'http://127.0.0.1:8001/api'

def req(method, path, data=None, token=None):
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(base + path, data=body, method=method,
                               headers={'Content-Type': 'application/json'} if body else {})
    if token:
        r.add_header('Authorization', 'Bearer ' + token)
    try:
        resp = urllib.request.urlopen(r, timeout=120)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

# 登录
s, d = req('POST', '/auth/login', {'username': 'admin', 'password': 'admin123'})
token = d['token']
print('登录:', s)

# 创建一个大理3天行程（不 seed）
s, d = req('POST', '/trips', {
    'depart_city': '北京', 'dest_city': '大理',
    'depart_date': '2026-11-10', 'return_date': '2026-11-12',
    'arrive_time': '12:00', 'depart_time': '16:00',
    'dest_cities': [{'city': '大理', 'days': 3}],
}, token)
trip_id = d['trip']['id']
print('创建行程:', s, 'id=', trip_id, d['trip']['title'])

# 调用 AI 规划
print('调用 AI 规划中（可能需要 10-30 秒）...')
t0 = time.time()
s, d = req('POST', '/trips/%d/ai-plan' % trip_id, token=token)
elapsed = time.time() - t0
print('AI 规划:', s, '耗时 %.1f 秒' % elapsed)
if s == 200:
    print('  生成节点数:', d.get('total_nodes'))
    print('  匹配真实POI数:', d.get('poi_matched'))
    print('  天数:', d.get('days'))
    # 打印每天节点
    for day in d.get('timeline', {}).get('days', []):
        print('  D%d (%s): %s' % (day['day_no'], day.get('city', ''),
              ' → '.join('%s(%s,%dm)' % (n['name'], n['node_type'], n['duration_minutes']) for n in day['nodes'])))
else:
    print('  错误:', d)
