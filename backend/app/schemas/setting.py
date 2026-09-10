# -*- coding: utf-8 -*-
from pydantic import BaseModel


class SettingOut(BaseModel):
    """设置项输出：敏感字段（api_key）脱敏显示。"""
    llm_base_url: str = ""
    llm_api_key: str = ""        # 输出时脱敏：有值显示 "••••••••"，无值显示 ""
    llm_model: str = ""
    amap_key: str = ""           # 输出时脱敏
    weather_provider: str = "open-meteo"


class SettingUpdate(BaseModel):
    """设置更新：传入空字符串表示清除；传入 None 表示不修改该字段。"""
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    amap_key: str | None = None
    weather_provider: str | None = None
