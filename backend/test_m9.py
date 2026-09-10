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

s, d = req('POST', '/auth/login', {'username': 'admin', 'password': 'admin123'})
token = d['token']

# 创建带交通方式和旅游要求的行程
s, d = req('POST', '/trips', {
    'depart_city': '北京', 'dest_city': '丽江',
    'depart_date': '2026-11-15', 'return_date': '2026-11-17',
    'arrive_time': '14:00', 'depart_time': '18:00',
    'dest_cities': [{'city': '丽江', 'days': 3}],
    'depart_transport': 'plane', 'arrive_station': '丽江三义机场',
    'return_transport': 'plane', 'depart_station': '丽江三义机场',
    'preferences': {'requirements': '住在丽江古城附近，喜欢安静的客栈，预算中等', 'pace': '休闲'},
}, token)
trip_id = d['trip']['id']
print('创建行程:', s, 'id=', trip_id)
print('  交通字段:', d['trip'].get('depart_transport'), d['trip'].get('arrive_station'),
      d['trip'].get('return_transport'), d['trip'].get('depart_station'))
print('  时间窗口:', [(w['day_no'], w['start'], w['end'], w['note']) for w in d['windows']])

# AI 规划
print('AI 规划中...')
t0 = time.time()
s, d = req('POST', '/trips/%d/ai-plan' % trip_id, token=token)
print('AI 规划:', s, '耗时 %.1f 秒' % (time.time() - t0))
if s == 200:
    print('  节点数:', d.get('total_nodes'), '匹配POI:', d.get('poi_matched'))
    # 检查 POI 清单
    s2, d2 = req('GET', '/trips/%d/pois' % trip_id, token=token)
    print('  行程POI清单数量:', len(d2) if isinstance(d2, list) else d2)
    if isinstance(d2, list):
        for p in d2[:5]:
            print('    -', p.get('name'), p.get('poi_type'), 'source=' + str(p.get('source')))
else:
    print('  错误:', d)
