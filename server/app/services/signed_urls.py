from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlencode

import jwt
from fastapi import HTTPException, status

from app.config import get_settings

MediaPurpose = Literal["stream", "download", "thumbnail"]


def mint_media_token(media_id: str, purpose: MediaPurpose) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.signed_url_hours)
    payload = {
        "sub": media_id,
        "purpose": purpose,
        "typ": "media",
        "exp": expire,
    }
    return jwt.encode(payload, get_settings().media_signing_secret, algorithm="HS256")


def verify_media_token(token: str, media_id: str, purpose: MediaPurpose) -> None:
    try:
        payload = jwt.decode(token, get_settings().media_signing_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Signed URL expired") from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signed URL") from exc
    if payload.get("typ") != "media" or payload.get("purpose") != purpose or payload.get("sub") != media_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signed URL")


def media_url(media_id: str, purpose: MediaPurpose) -> str:
    token = mint_media_token(media_id, purpose)
    base = get_settings().public_base_url.rstrip("/")
    query = urlencode({"token": token})
    return f"{base}/api/v1/media/{media_id}/{purpose}?{query}"
