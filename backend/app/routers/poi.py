# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.itinerary import PoiSummary
from ..services import poi_service

router = APIRouter(prefix="/api/pois", tags=["poi"])


@router.get("/search", response_model=list[PoiSummary])
def search_pois(city: str | None = Query(None, description="城市，如：大理"),
                q: str | None = Query(None, description="名称关键字"),
                type: str | None = Query(None, description="hotel/attraction/restaurant"),
                limit: int = Query(30, ge=1, le=50),
                db: Session = Depends(get_db)):
    """检索真实地点池（内置示例数据；接入高德后自动合并外部来源）。"""
    pois = poi_service.search_pois(db, city=city, keyword=q, poi_type=type, limit=limit)
    return [PoiSummary.model_validate(p) for p in pois]


@router.post("/seed", status_code=200)
def seed(db: Session = Depends(get_db)):
    """初始化内置 POI 示例库（幂等）。"""
    added = poi_service.seed_pois(db)
    return {"seeded": added, "message": f"新增 {added} 条示例 POI"}
