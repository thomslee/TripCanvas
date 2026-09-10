# -*- coding: utf-8 -*-
"""管理员：用户管理（列表、修改角色）。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import User

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UserAdminOut(BaseModel):
    id: int
    username: str
    nickname: str | None
    role: str
    created_at: str | None

    class Config:
        from_attributes = True


class RoleUpdateIn(BaseModel):
    role: str  # admin / user


@router.get("/users", response_model=list[UserAdminOut])
def list_users(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    """管理员：全部用户列表。"""
    users = db.query(User).order_by(User.id).all()
    return [
        UserAdminOut(
            id=u.id, username=u.username, nickname=u.nickname,
            role=u.role, created_at=u.created_at.isoformat() if u.created_at else None,
        )
        for u in users
    ]


@router.patch("/users/{user_id}", response_model=UserAdminOut)
def update_user_role(user_id: int, data: RoleUpdateIn, db: Session = Depends(get_db),
                     _admin=Depends(require_admin)):
    """管理员：修改用户角色。"""
    if data.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="角色只能是 admin 或 user")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.role = data.role
    db.commit()
    db.refresh(user)
    return UserAdminOut(
        id=user.id, username=user.username, nickname=user.nickname,
        role=user.role, created_at=user.created_at.isoformat() if user.created_at else None,
    )
