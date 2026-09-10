# -*- coding: utf-8 -*-
import datetime as dt
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DestCity(BaseModel):
    """多城市行程的单个目的城市与停留天数。"""
    city: str = Field(..., max_length=64, description="目的城市")
    days: int = Field(..., ge=1, description="该城市停留天数")


class TripCreate(BaseModel):
    depart_city: str = Field(..., max_length=64, description="出发城市")
    dest_city: str = Field(..., max_length=64, description="目的城市")
    depart_date: dt.date = Field(..., description="去程日期")
    arrive_time: Optional[dt.time] = Field(None, description="去程到达时刻")
    return_date: dt.date = Field(..., description="返程日期")
    depart_time: Optional[dt.time] = Field(None, description="返程起飞时刻")
    preferences: Optional[dict] = Field(None, description="偏好：兴趣/节奏/预算/人数/旅游要求等")
    title: Optional[str] = Field(None, max_length=128, description="自定义标题，缺省自动生成")
    dest_cities: Optional[List[DestCity]] = Field(
        None, description="多城市目的地，如[{city:'成都',days:2},{city:'重庆',days:3}]；缺省=单城市")
    depart_transport: Optional[str] = Field(None, description="去程交通方式：plane/train/ship/car")
    arrive_station: Optional[str] = Field(None, max_length=64, description="到达站点（机场/高铁站名）")
    return_transport: Optional[str] = Field(None, description="返程交通方式：plane/train/ship/car")
    depart_station: Optional[str] = Field(None, max_length=64, description="返程出发站点")


class DayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    day_no: int
    date: Optional[dt.date] = None
    theme: Optional[str] = None
    city: Optional[str] = None


class TripOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: Optional[str] = None
    depart_city: str
    dest_city: str
    depart_date: dt.date
    arrive_time: Optional[dt.time] = None
    return_date: dt.date
    depart_time: Optional[dt.time] = None
    total_days: int
    status: str
    preferences: Optional[dict] = None
    dest_cities: Optional[list] = None
    depart_transport: Optional[str] = None
    arrive_station: Optional[str] = None
    return_transport: Optional[str] = None
    depart_station: Optional[str] = None
    ai_version: Optional[str] = None
    created_at: dt.datetime
    days: List[DayOut] = []


class DayWindowOut(BaseModel):
    day_no: int
    date: str
    start: str
    end: str
    note: str


class TripCreateOut(BaseModel):
    trip: TripOut
    windows: List[DayWindowOut] = []
    messages: List[str] = []
