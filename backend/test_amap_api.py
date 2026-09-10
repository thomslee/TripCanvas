# -*- coding: utf-8 -*-
import urllib.request, urllib.parse, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
base = 'http://127.0.0.1:8001/api'

r = urllib.request.Request(base + '/auth/login',
    data=json.dumps({'username':'admin','password':'admin123'}).encode(),
    headers={'Content-Type':'application/json'})
token = json.loads(urllib.request.urlopen(r).read())['token']

# 测试高德搜索
q = urllib.parse.urlencode({'q':'超意兴把子肉','city':'济南','limit':3})
r2 = urllib.request.Request(base + '/pois/search-amap?' + q,
    headers={'Authorization':'Bearer '+token})
d = json.loads(urllib.request.urlopen(r2, timeout=15).read().decode())
print('高德搜索结果:', len(d), '条')
for x in d:
    print(' -', x['name'], '|', x['poi_type'], '| rating:', x.get('rating'),
          '|', x.get('address'), '| source:', x.get('source'))

# 测试酒店搜索
q2 = urllib.parse.urlencode({'q':'大明湖酒店','city':'济南','limit':3})
r3 = urllib.request.Request(base + '/pois/search-amap?' + q2,
    headers={'Authorization':'Bearer '+token})
d2 = json.loads(urllib.request.urlopen(r3, timeout=15).read().decode())
print('\n酒店搜索结果:', len(d2), '条')
for x in d2:
    print(' -', x['name'], '|', x['poi_type'], '| rating:', x.get('rating'),
          '|', x.get('address'), '| source:', x.get('source'))
