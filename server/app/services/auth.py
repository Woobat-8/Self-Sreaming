from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.refresh_token import RefreshToken
from app.models.user import User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_refresh_token(db: Session, user: User) -> str:
    raw = secrets.token_urlsafe(48)
    record = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(days=get_settings().refresh_token_days),
    )
    db.add(record)
    db.commit()
    return raw


def get_valid_refresh(db: Session, raw_token: str) -> RefreshToken | None:
    token_hash = hash_refresh_token(raw_token)
    record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if record is None or record.revoked_at is not None:
        return None
    expires = record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        return None
    return record


def revoke_refresh(db: Session, record: RefreshToken) -> None:
    record.revoked_at = datetime.now(timezone.utc)
    db.commit()


def create_user(db: Session, username: str, password: str, role: str = "member") -> User:
    existing = db.scalar(select(User).where(User.username == username))
    if existing is not None:
        raise ValueError(f"User already exists: {username}")
    user = User(username=username, password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_password(db: Session, username: str, password: str) -> User:
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        raise ValueError(f"User not found: {username}")
    user.password_hash = hash_password(password)
    db.commit()
    return user


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def bootstrap_admin_if_needed(db: Session) -> None:
    settings = get_settings()
    user = settings.bootstrap_admin_user.strip()
    password = settings.bootstrap_admin_password
    if not user or not password:
        return
    if db.scalar(select(User).where(User.username == user)):
        return
    if db.scalar(select(User.id).limit(1)):
        return
    create_user(db, user, password, role="admin")
