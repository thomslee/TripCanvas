# -*- coding: utf-8 -*-
import sys, io, json, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from app.database import SessionLocal
from app.services import setting_service

db = SessionLocal()
base = setting_service.get_value(db, 'llm_base_url').rstrip('/') + '/v1'
key = setting_service.get_value(db, 'llm_api_key')
model = setting_service.get_value(db, 'llm_model')
db.close()

print('配置: base=%s, model=%s' % (base, model))
print()

# 测试1：简单对话
url = base + '/chat/completions'
data = json.dumps({
    'model': model,
    'messages': [{'role': 'user', 'content': '你好，请用一句话介绍你自己'}],
    'max_tokens': 100,
    'temperature': 0.7,
}).encode()
req = urllib.request.Request(url, data=data,
                             headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key},
                             method='POST')
r = urllib.request.urlopen(req, timeout=20)
d = json.loads(r.read().decode())
print('=== 测试1: 简单对话 ===')
print('状态:', r.status)
print('usage:', d.get('usage'))
print('回复:', d['choices'][0]['message']['content'][:100])
print()

# 测试2：行程规划能力（模拟系统 prompt）
prompt = """你是一个旅游行程规划助手。请为以下行程生成每日安排：
- 目的地：大理
- 天数：3天2晚
- 出发地：北京
- 到达时间：第一天中午12点
- 返程时间：第三天下午4点
- 偏好：休闲、美食、拍照

请按天输出，每天包含3-5个节点（景点/餐厅/酒店），每个节点给出名称、类型、建议停留时长。用JSON格式输出。"""

data2 = json.dumps({
    'model': model,
    'messages': [{'role': 'user', 'content': prompt}],
    'max_tokens': 800,
    'temperature': 0.7,
    'response_format': {'type': 'json_object'},
}).encode()
req2 = urllib.request.Request(url, data=data2,
                              headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key},
                              method='POST')
r2 = urllib.request.urlopen(req2, timeout=30)
d2 = json.loads(r2.read().decode())
print('=== 测试2: 行程规划（JSON输出） ===')
print('状态:', r2.status)
print('usage:', d2.get('usage'))
content = d2['choices'][0]['message']['content']
print('回复长度:', len(content))
print('回复前300字:', content[:300])
print()
print('=== deepseek-chat 完全可用 ===')
