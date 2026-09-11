# -*- coding: utf-8 -*-
import datetime as dt
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PoiSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city: Optional[str] = None
    poi_type: Optional[str] = None
    name: str
    address: Optional[str] = None
    open_hours: Optional[str] = None
    phone: Optional[str] = None
    ticket_price: Optional[str] = None
    rating: Optional[float] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    source: Optional[str] = None


class NodeBase(BaseModel):
    node_type: str = Field(..., description="hotel/attraction/restaurant")
    name: str = Field(..., max_length=128)
    duration_minutes: int = Field(60, ge=10, le=1440)
    note: Optional[str] = Field(None, max_length=255)
    poi_id: Optional[int] = Field(None, description="关联真实 POI（缺省则按名称）")
    after_node_id: Optional[int] = Field(None, description="插入到该节点之后；缺省追加到当天末尾")


class NodeCreate(NodeBase):
    pass


class NodePatch(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    node_type: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=10, le=1440)
    note: Optional[str] = Field(None, max_length=255)
    poi_id: Optional[int] = Field(None, description="设为 POI id 关联真实地点；传 0 清除关联")


class NodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    node_type: str
    name: str
    duration_minutes: int
    sort_order: int
    note: Optional[str] = None
    poi_id: Optional[int] = None
    poi: Optional[PoiSummary] = None
    # 由时间线计算得出，仅展示不落库
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class EdgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_node_id: int
    to_node_id: int
    transport: str
    duration_minutes: int
    distance_km: Optional[float] = None
    note: Optional[str] = None


class EdgePatch(BaseModel):
    transport: Optional[str] = Field(None, description="plane/train/ship/car/taxi/bus/metro/bike/walk")
    duration_minutes: Optional[int] = Field(None, ge=1, le=1440)


class DayTimelineOut(BaseModel):
    day_no: int
    date: str
    city: Optional[str] = None
    window_start: str
    window_end: str
    note: str
    total_used_min: int
    conflict: bool
    overflow_min: int
    nodes: List[NodeOut] = []
    edges: List[EdgeOut] = []


class TimelineOut(BaseModel):
    trip_id: int
    title: Optional[str] = None
    dest_city: Optional[str] = None
    dest_cities: Optional[list] = None
    days: List[DayTimelineOut] = []


class MovePayload(BaseModel):
    direction: str = Field(..., description="up/down")


class ReorderPayload(BaseModel):
    node_ids: List[int] = Field(..., min_length=1)


class TripPoiOut(BaseModel):
    """行程中使用到的真实地点（去重）+ 出现信息。"""
    poi: PoiSummary
    count: int = Field(0, description="在轨迹图中出现的节点数")
    node_ids: List[int] = Field(default_factory=list)
