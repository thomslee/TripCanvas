# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.setting import SettingOut, SettingUpdate
from ..services import setting_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingOut)
def get_settings(db: Session = Depends(get_db)):
    """读取全部设置（敏感字段脱敏）。"""
    return SettingOut(**setting_service.get_masked(db))


@router.put("", response_model=SettingOut)
def update_settings(payload: SettingUpdate, db: Session = Depends(get_db)):
    """批量更新设置；传 None 不修改，传空字符串清除。"""
    updates = payload.model_dump(exclude_none=True)
    return SettingOut(**setting_service.update(db, updates))
