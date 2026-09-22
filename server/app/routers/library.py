from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.media import MediaItem
from app.models.user import User
from app.schemas import LibraryResponse, MediaItemOut, MediaUrls
from app.services.signed_urls import media_url

router = APIRouter(prefix="/api/v1", tags=["library"])


def to_out(item: MediaItem) -> MediaItemOut:
    thumb = media_url(item.id, "thumbnail") if item.thumbnail_relpath else None
    return MediaItemOut(
        id=item.id,
        filename=item.filename,
        type=item.media_type,
        mime_type=item.mime_type,
        size_bytes=item.size_bytes,
        duration_seconds=item.duration_seconds,
        width=item.width,
        height=item.height,
        urls=MediaUrls(
            stream=media_url(item.id, "stream"),
            download=media_url(item.id, "download"),
            thumbnail=thumb,
        ),
    )


@router.get("/library", response_model=LibraryResponse)
def list_library(
    type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> LibraryResponse:
    if type is not None and type not in {"video", "image"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="type must be video or image")
    filters = [MediaItem.playable.is_(True)]
    if type:
        filters.append(MediaItem.media_type == type)
    total = db.scalar(select(func.count()).select_from(MediaItem).where(*filters)) or 0
    items = (
        db.scalars(
            select(MediaItem)
            .where(*filters)
            .order_by(MediaItem.filename)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .all()
    )
    return LibraryResponse(
        items=[to_out(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )
