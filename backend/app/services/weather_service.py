# -*- coding: utf-8 -*-
"""天气服务：代理 open-meteo（无需 Key），按城市名取当天天气 + 穿衣建议 + 未来 3 天预报；失败优雅降级。"""
import json
import re
import time
import urllib.parse
import urllib.request
from typing import Optional

# WMO 天气代码 -> 中文描述
WMO_MAP = {
    0: "晴", 1: "大部晴朗", 2: "多云", 3: "阴",
    45: "雾", 48: "雾凇",
    51: "毛毛雨", 53: "毛毛雨", 55: "毛毛雨", 56: "冻毛毛雨", 57: "冻毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨", 66: "冻雨", 67: "冻雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
    80: "小阵雨", 81: "中阵雨", 82: "强阵雨",
    85: "小阵雪", 86: "强阵雪",
    95: "雷阵雨", 96: "雷阵雨伴冰雹", 99: "强雷阵雨伴冰雹",
}

# 天气码 -> 图标 key（前端按 key 渲染 SVG）
WMO_ICON = {
    0: "sun", 1: "sun", 2: "cloud", 3: "cloud",
    45: "fog", 48: "fog",
    51: "rain", 53: "rain", 55: "rain", 56: "rain", 57: "rain",
    61: "rain", 63: "rain", 65: "rain", 66: "rain", 67: "rain",
    71: "snow", 73: "snow", 75: "snow", 77: "snow",
    80: "rain", 81: "rain", 82: "rain",
    85: "snow", 86: "snow",
    95: "thunder", 96: "thunder", 99: "thunder",
}

_RAIN = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}
_SNOW = {71, 73, 75, 77, 85, 86}
_THUNDER = {95, 96, 99}
_FOG = {45, 48}

_cache: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 600  # 10 分钟


def _http_get(url: str, timeout: float = 5.0) -> Optional[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "TripCanvas/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def _geocode(city: str) -> Optional[tuple[float, float]]:
    q = urllib.parse.quote(city)
    data = _http_get(
        f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count=1&language=zh&format=json")
    if not data or not data.get("results"):
        return None
    r = data["results"][0]
    return r.get("latitude"), r.get("longitude")


def dress_advice(temp: int, code: int) -> str:
    """穿衣建议：温度为主，天气码为辅。"""
    if temp >= 30:
        base = "短袖速干衣，注意防晒补水"
    elif temp >= 24:
        base = "短袖或薄长袖，轻便为主"
    elif temp >= 17:
        base = "长袖 T 恤加薄外套"
    elif temp >= 10:
        base = "外套或卫衣加长裤"
    elif temp >= 3:
        base = "厚外套或大衣，注意保暖"
    else:
        base = "羽绒服，全副保暖"
    if code in _RAIN:
        base += "，记得带伞"
    elif code in _SNOW:
        base += "，注意防滑保暖"
    elif code in _THUNDER:
        base += "，避免户外空旷处"
    elif code in _FOG:
        base += "，出行注意能见度"
    return base


def _fmt_date(d: str) -> str:
    """2026-09-10 -> 09/10"""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", d)
    return f"{m.group(2)}/{m.group(3)}" if m else d


def get_weather(city: str) -> dict:
    """返回 {available, city, date, desc, icon, temp, feels, temp_min, temp_max, advice, forecast[]}"""
    now = time.time()
    cached = _cache.get(city)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]

    geo = _geocode(city)
    if not geo:
        out = {"available": False, "city": city, "message": "未定位到该城市"}
        _cache[city] = (now, out)
        return out

    lat, lon = geo
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           f"&current=temperature_2m,apparent_temperature,weather_code"
           f"&daily=weather_code,temperature_2m_max,temperature_2m_min"
           f"&timezone=Asia%2FShanghai&forecast_days=6")
    data = _http_get(url)
    if not data or "current" not in data:
        out = {"available": False, "city": city, "message": "天气服务暂不可用"}
        _cache[city] = (now, out)
        return out

    cur = data["current"]
    day = data["daily"]
    code = cur.get("weather_code", 0)
    temp = round(cur.get("temperature_2m", 0))
    forecast = []
    for i, d in enumerate(day.get("time", [])[:5]):
        dc = day["weather_code"][i] if day.get("weather_code") else 0
        forecast.append({
            "date": _fmt_date(d),
            "desc": WMO_MAP.get(dc, "多云"),
            "icon": WMO_ICON.get(dc, "cloud"),
            "temp_min": round(day["temperature_2m_min"][i]) if day.get("temperature_2m_min") else None,
            "temp_max": round(day["temperature_2m_max"][i]) if day.get("temperature_2m_max") else None,
        })
    out = {
        "available": True,
        "city": city,
        "date": _fmt_date(day["time"][0]) if day.get("time") else None,
        "desc": WMO_MAP.get(code, "多云"),
        "icon": WMO_ICON.get(code, "cloud"),
        "temp": temp,
        "feels": round(cur.get("apparent_temperature", 0)),
        "temp_min": round(day["temperature_2m_min"][0]) if day.get("temperature_2m_min") else None,
        "temp_max": round(day["temperature_2m_max"][0]) if day.get("temperature_2m_max") else None,
        "advice": dress_advice(temp, code),
        "forecast": forecast,
    }
    _cache[city] = (now, out)
    return out
