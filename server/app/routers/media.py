from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from starlette.responses import FileResponse

from app.database import get_db
from app.deps import get_current_user
from app.models.media import MediaItem
from app.models.user import User
from app.routers.library import to_out
from app.schemas import MediaItemOut
from app.services.files import file_response
from app.services.scanner import resolve_media_file, resolve_thumbnail
from app.services.signed_urls import MediaPurpose, verify_media_token

router = APIRouter(prefix="/api/v1/media", tags=["media"])


def _get_item(db: Session, media_id: str, *, playable_only: bool = True) -> MediaItem:
    item = db.get(MediaItem, media_id)
    if item is None or (playable_only and not item.playable):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    return item


def _require_signed(media_id: str, purpose: MediaPurpose, token: str | None) -> None:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Signed token required")
    verify_media_token(token, media_id, purpose)


@router.get("/{media_id}", response_model=MediaItemOut)
def get_media(
    media_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> MediaItemOut:
    return to_out(_get_item(db, media_id))


@router.get("/{media_id}/stream")
def stream_media(
    media_id: str,
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> FileResponse:
    _require_signed(media_id, "stream", token)
    item = _get_item(db, media_id)
    path = resolve_media_file(item)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing")
    return file_response(path, item.mime_type)


@router.get("/{media_id}/download")
def download_media(
    media_id: str,
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> FileResponse:
    _require_signed(media_id, "download", token)
    item = _get_item(db, media_id)
    path = resolve_media_file(item)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing")
    return file_response(path, item.mime_type, as_attachment=True, filename=item.filename)


@router.get("/{media_id}/thumbnail")
def thumbnail_media(
    media_id: str,
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> FileResponse:
    _require_signed(media_id, "thumbnail", token)
    item = _get_item(db, media_id)
    path = resolve_thumbnail(item)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not found")
    return file_response(path, "image/jpeg")
