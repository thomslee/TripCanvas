# -*- coding: utf-8 -*-
import urllib.request, json, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
base = 'http://127.0.0.1:8001/api'

r = urllib.request.Request(base + '/auth/login',
    data=json.dumps({'username':'admin','password':'admin123'}).encode(),
    headers={'Content-Type':'application/json'})
token = json.loads(urllib.request.urlopen(r).read())['token']

# 先看替换前有多少AI推荐节点
r2 = urllib.request.Request(base + '/trips/52/timeline', headers={'Authorization':'Bearer '+token})
tl = json.loads(urllib.request.urlopen(r2).read().decode())
ai_count = sum(1 for d in tl['days'] for n in d['nodes'] if n.get('poi') and n['poi'].get('source')=='ai')
real_count = sum(1 for d in tl['days'] for n in d['nodes'] if n.get('poi') and n['poi'].get('source') in ('gaode','seed'))
print('替换前: AI推荐=%d, 真实=%d' % (ai_count, real_count))

# 一键替换
print('正在一键替换...')
t0 = time.time()
r3 = urllib.request.Request(base + '/trips/52/auto-replace-pois',
    data=b'', headers={'Authorization':'Bearer '+token}, method='POST')
result = json.loads(urllib.request.urlopen(r3, timeout=60).read().decode())
print('替换完成，耗时 %.1f 秒' % (time.time()-t0))
print('成功: %d, 失败: %d' % (result['replaced'], result['failed']))
for item in result['items']:
    status = '✓' if item['status']=='ok' else '✗'
    print('  %s %s → %s' % (status, item['old'], item.get('new') or '未找到'))

# 替换后统计
r4 = urllib.request.Request(base + '/trips/52/timeline', headers={'Authorization':'Bearer '+token})
tl2 = json.loads(urllib.request.urlopen(r4).read().decode())
ai_count2 = sum(1 for d in tl2['days'] for n in d['nodes'] if n.get('poi') and n['poi'].get('source')=='ai')
real_count2 = sum(1 for d in tl2['days'] for n in d['nodes'] if n.get('poi') and n['poi'].get('source') in ('gaode','seed'))
print('替换后: AI推荐=%d, 真实=%d' % (ai_count2, real_count2))
