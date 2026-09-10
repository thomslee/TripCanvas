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

def test(url):
    data = json.dumps({'model': model, 'messages': [{'role': 'user', 'content': '你好，请用一句话回复'}], 'max_tokens': 50, 'temperature': 0.7}).encode()
    req = urllib.request.Request(url + '/chat/completions', data=data,
                                 headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key},
                                 method='POST')
    try:
        r = urllib.request.urlopen(req, timeout=15)
        d = json.loads(r.read().decode())
        return True, d['choices'][0]['message']['content'][:80]
    except urllib.error.HTTPError as e:
        return False, 'HTTP %d: %s' % (e.code, e.read().decode()[:200])
    except Exception as e:
        return False, str(e)[:200]

print('配置: base=%s, model=%s' % (base, model))
print()

ok, msg = test(base)
print('测试 %s/chat/completions:' % base)
print('  结果: %s - %s' % ('OK' if ok else 'FAIL', msg))
print()

base2 = base.rstrip('/') + '/v1'
ok, msg = test(base2)
print('测试 %s/chat/completions:' % base2)
print('  结果: %s - %s' % ('OK' if ok else 'FAIL', msg))
