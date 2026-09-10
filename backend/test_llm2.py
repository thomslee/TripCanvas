# -*- coding: utf-8 -*-
import sys, io, json, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from app.database import SessionLocal
from app.services import setting_service

db = SessionLocal()
base = setting_service.get_value(db, 'llm_base_url')
key = setting_service.get_value(db, 'llm_api_key')
model = setting_service.get_value(db, 'llm_model')
db.close()

url = base.rstrip('/') + '/v1/chat/completions'
data = json.dumps({
    'model': model,
    'messages': [{'role': 'user', 'content': '你好，请用一句话介绍你自己'}],
    'max_tokens': 200,
    'temperature': 0.7,
}).encode()
req = urllib.request.Request(url, data=data,
                             headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key},
                             method='POST')
try:
    r = urllib.request.urlopen(req, timeout=20)
    d = json.loads(r.read().decode())
    print('状态:', r.status)
    print('模型:', d.get('model'))
    print('usage:', d.get('usage'))
    print('内容:', repr(d['choices'][0]['message'].get('content', '')))
    print('finish_reason:', d['choices'][0].get('finish_reason'))
except urllib.error.HTTPError as e:
    print('HTTP错误:', e.code)
    print(e.read().decode()[:500])
except Exception as e:
    print('异常:', e)
