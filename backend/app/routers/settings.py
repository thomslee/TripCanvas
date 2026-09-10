# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import require_admin
from ..models import User
from ..schemas.setting import SettingOut, SettingUpdate
from ..services import setting_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingOut)
def get_settings(db: Session = Depends(get_db),
                 _admin: User = Depends(require_admin)):
    """读取全部设置（敏感字段脱敏）。仅管理员。"""
    return SettingOut(**setting_service.get_masked(db))


@router.put("", response_model=SettingOut)
def update_settings(payload: SettingUpdate, db: Session = Depends(get_db),
                    _admin: User = Depends(require_admin)):
    """批量更新设置；传 None 不修改，传空字符串清除。仅管理员。"""
    updates = payload.model_dump(exclude_none=True)
    return SettingOut(**setting_service.update(db, updates))
