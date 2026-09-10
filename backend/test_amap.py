# -*- coding: utf-8 -*-
import urllib.request, urllib.parse, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

key = 'f724edc8e022ce60d793f10562cecea3'

# 测试1：POI 搜索（济南的餐厅）
params = urllib.parse.urlencode({
    'keywords': '超意兴把子肉',
    'city': '济南',
    'key': key,
    'offset': 3,
    'extensions': 'all',
})
url = 'https://restapi.amap.com/v3/place/text?' + params
try:
    r = urllib.request.urlopen(url, timeout=15)
    d = json.loads(r.read().decode())
    print('=== POI搜索 ===')
    print('status:', d.get('status'), 'info:', d.get('info'), 'count:', d.get('count'))
    for p in d.get('pois', [])[:3]:
        print(' -', p.get('name'), '|', p.get('address'), '| tel:', p.get('tel'), '| rating:', p.get('biz_ext', {}).get('rating'))
except Exception as e:
    print('POI搜索失败:', e)

# 测试2：酒店搜索
params2 = urllib.parse.urlencode({
    'keywords': '大明湖附近酒店',
    'city': '济南',
    'key': key,
    'offset': 3,
    'extensions': 'all',
})
url2 = 'https://restapi.amap.com/v3/place/text?' + params2
try:
    r2 = urllib.request.urlopen(url2, timeout=15)
    d2 = json.loads(r2.read().decode())
    print('\n=== 酒店搜索 ===')
    print('status:', d2.get('status'), 'count:', d2.get('count'))
    for p in d2.get('pois', [])[:3]:
        print(' -', p.get('name'), '|', p.get('address'), '| rating:', p.get('biz_ext', {}).get('rating'))
except Exception as e:
    print('酒店搜索失败:', e)
