# -*- coding: utf-8 -*-
from fastapi import APIRouter, Query

from ..services.weather_service import get_weather

router = APIRouter(prefix="/api", tags=["weather"])


@router.get("/weather")
def weather(city: str = Query(..., min_length=1, max_length=32, description="城市名，如：大理")):
    """按城市名返回当天天气（open-meteo 代理，无需 Key）。"""
    return get_weather(city)
