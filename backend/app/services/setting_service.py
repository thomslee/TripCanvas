# -*- coding: utf-8 -*-
"""应用设置服务：大模型 API、高德 Key 等外部连接配置，key-value 存储。"""
from sqlalchemy.orm import Session
from ..models import AppSetting

# 允许配置的 key 白名单
ALLOWED_KEYS = {"llm_base_url", "llm_api_key", "llm_model", "amap_key", "weather_provider"}

# 需要脱敏输出的 key（api_key 类）
SENSITIVE_KEYS = {"llm_api_key", "amap_key"}

DEFAULTS = {
    "llm_base_url": "",
    "llm_api_key": "",
    "llm_model": "",
    "amap_key": "",
    "weather_provider": "open-meteo",
}


def get_all(db: Session) -> dict[str, str]:
    """读取全部设置，缺失的 key 用默认值补齐。"""
    rows = db.query(AppSetting).all()
    result = dict(DEFAULTS)
    for r in rows:
        if r.skey in ALLOWED_KEYS:
            result[r.skey] = r.svalue or ""
    return result


def get_masked(db: Session) -> dict[str, str]:
    """读取全部设置，敏感字段脱敏（有值显示 ••••••••）。"""
    data = get_all(db)
    for k in SENSITIVE_KEYS:
        if data.get(k):
            data[k] = "••••••••"
    return data


def update(db: Session, updates: dict[str, str | None]) -> dict[str, str]:
    """批量更新设置：None 表示不修改，空字符串表示清除。"""
    for key, value in updates.items():
        if key not in ALLOWED_KEYS or value is None:
            continue
        row = db.get(AppSetting, key)
        if row:
            row.svalue = value
        else:
            db.add(AppSetting(skey=key, svalue=value))
    db.commit()
    return get_masked(db)


def get_value(db: Session, key: str) -> str:
    """读取单个设置的真实值（供后端内部调用，不脱敏）。"""
    if key not in ALLOWED_KEYS:
        return ""
    row = db.get(AppSetting, key)
    return row.svalue if row and row.svalue else DEFAULTS.get(key, "")
