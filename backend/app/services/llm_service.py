# -*- coding: utf-8 -*-
"""大模型调用服务：OpenAI 兼容接口（DeepSeek / 通义 / GPT 等）。"""
import json
import urllib.request
import urllib.error
from sqlalchemy.orm import Session
from ..services import setting_service


class LLMError(Exception):
    pass


def _get_config(db: Session) -> dict:
    return {
        'base_url': setting_service.get_value(db, 'llm_base_url') or 'https://api.deepseek.com/v1',
        'api_key': setting_service.get_value(db, 'llm_api_key') or '',
        'model': setting_service.get_value(db, 'llm_model') or 'deepseek-chat',
    }


def chat(db: Session, messages: list[dict], temperature: float = 0.7,
         max_tokens: int = 1500, response_format: str | None = None,
         timeout: int = 60) -> str:
    """调用大模型对话接口，返回 assistant 文本内容。"""
    cfg = _get_config(db)
    if not cfg['api_key']:
        raise LLMError('未配置大模型 API Key，请在设置中配置')

    base = cfg['base_url'].rstrip('/')
    if not base.endswith('/v1'):
        base += '/v1'
    url = base + '/chat/completions'

    payload = {
        'model': cfg['model'],
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
    }
    if response_format == 'json':
        payload['response_format'] = {'type': 'json_object'}

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + cfg['api_key'],
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        content = data['choices'][0]['message'].get('content', '')
        if not content:
            raise LLMError('大模型返回空内容')
        return content
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')[:300]
        raise LLMError(f'大模型接口错误 {e.code}: {body}')
    except Exception as e:
        raise LLMError(f'大模型调用失败: {e}')


def chat_json(db: Session, messages: list[dict], temperature: float = 0.7,
              max_tokens: int = 1500, timeout: int = 60) -> dict:
    """调用大模型并解析 JSON 返回。失败时尝试从文本中提取 JSON。"""
    content = chat(db, messages, temperature=temperature, max_tokens=max_tokens,
                   response_format='json', timeout=timeout)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # 尝试提取第一个 { 到最后一个 }
        start = content.find('{')
        end = content.rfind('}')
        if start >= 0 and end > start:
            try:
                return json.loads(content[start:end + 1])
            except json.JSONDecodeError:
                pass
        raise LLMError(f'大模型返回非 JSON 格式: {content[:200]}')
