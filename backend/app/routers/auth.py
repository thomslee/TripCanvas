# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=4, max_length=128)
    nickname: str | None = None


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    nickname: str | None
    role: str
    gender: str | None = None
    age: int | None = None
    identity: str | None = None
    preferences: list[str] | None = None

    class Config:
        from_attributes = True


class AuthOut(BaseModel):
    token: str
    user: UserOut


class ProfileUpdateIn(BaseModel):
    nickname: str | None = None
    gender: str | None = None
    age: int | None = None
    identity: str | None = None
    preferences: list[str] | None = None


@router.post("/register", response_model=AuthOut, status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    user, token = auth_service.register(db, data.username, data.password, data.nickname)
    if not user:
        raise HTTPException(status_code=409, detail="用户名已存在")
    return AuthOut(token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=AuthOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user, token = auth_service.authenticate(db, data.username, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return AuthOut(token=token, user=UserOut.model_validate(user))


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=4, max_length=128)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserOut)
def update_profile(data: ProfileUpdateIn, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    """更新当前用户资料（昵称、性别、年龄、身份、喜好）。"""
    if data.nickname is not None:
        current_user.nickname = data.nickname
    if data.gender is not None:
        current_user.gender = data.gender
    if data.age is not None:
        current_user.age = data.age
    if data.identity is not None:
        current_user.identity = data.identity
    if data.preferences is not None:
        current_user.preferences = data.preferences
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/me/password", status_code=200)
def change_password(data: ChangePasswordIn, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    """修改当前用户密码。"""
    if not auth_service.verify_password(data.old_password, current_user.password_hash or ""):
        raise HTTPException(status_code=400, detail="原密码错误")
    current_user.password_hash = auth_service.hash_password(data.new_password)
    db.commit()
    return {"ok": True, "message": "密码已更新"}
