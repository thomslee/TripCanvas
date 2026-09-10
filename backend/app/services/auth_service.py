# -*- coding: utf-8 -*-
"""认证服务：密码哈希（pbkdf2）+ HMAC 签名 token（无外部依赖）。"""
import hashlib
import hmac
import base64
import json
import time
import os
from typing import Optional, Tuple

from sqlalchemy.orm import Session
from ..models import User

# token 签名密钥（生产应从环境变量读取，这里用固定值+机器标识）
_SECRET = os.environ.get("TRIPCANVAS_SECRET", "tripcanvas-dev-secret-key-2026")
_TOKEN_TTL = 7 * 24 * 3600  # 7 天


def hash_password(password: str) -> str:
    """pbkdf2_hmac 哈希，格式：pbkdf2$iterations$salt_hex$hash_hex"""
    salt = os.urandom(16)
    iterations = 100_000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2${iterations}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt_hex, hash_hex = stored.split("$")
        if scheme != "pbkdf2":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s.encode("ascii"))


def create_token(user_id: int, role: str) -> str:
    """生成 signed token：header.payload.signature"""
    payload = {"uid": user_id, "role": role, "exp": int(time.time()) + _TOKEN_TTL}
    payload_b = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    header_b = _b64encode(b'{"alg":"HS256","typ":"JWT"}')
    signing_input = f"{header_b}.{payload_b}"
    sig = hmac.new(_SECRET.encode("utf-8"), signing_input.encode("utf-8"),
                   hashlib.sha256).digest()
    return f"{signing_input}.{_b64encode(sig)}"


def decode_token(token: str) -> Optional[dict]:
    """验证并解析 token，失败返回 None"""
    try:
        header_b, payload_b, sig_b = token.split(".")
        signing_input = f"{header_b}.{payload_b}"
        expected_sig = hmac.new(_SECRET.encode("utf-8"), signing_input.encode("utf-8"),
                                hashlib.sha256).digest()
        if not hmac.compare_digest(_b64decode(sig_b), expected_sig):
            return None
        payload = json.loads(_b64decode(payload_b))
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


def authenticate(db: Session, username: str, password: str) -> Tuple[Optional[User], Optional[str]]:
    """验证用户名密码，返回 (user, token) 或 (None, None)"""
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.password_hash:
        return None, None
    if not verify_password(password, user.password_hash):
        return None, None
    token = create_token(user.id, user.role)
    return user, token


def register(db: Session, username: str, password: str, nickname: str = None,
             role: str = "user") -> Tuple[Optional[User], Optional[str]]:
    """注册新用户，返回 (user, token)；用户名重复返回 (None, None)"""
    if db.query(User).filter(User.username == username).first():
        return None, None
    user = User(username=username, password_hash=hash_password(password),
                nickname=nickname or username, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_token(user.id, user.role)
    return user, token


def ensure_admin(db: Session, username: str = "admin", password: str = "admin123"):
    """确保默认管理员账号存在"""
    if not db.query(User).filter(User.username == username).first():
        user = User(username=username, password_hash=hash_password(password),
                    nickname="管理员", role="admin")
        db.add(user)
        db.commit()
