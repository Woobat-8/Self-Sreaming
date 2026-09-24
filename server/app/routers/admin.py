from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import require_admin
from app.models.media import MediaItem
from app.models.user import User
from app.schemas import OnboardingQrResponse, ScanResponse
from app.services.scanner import resolve_thumbnail, scan_library

router = APIRouter(prefix="/api/v1", tags=["admin"])


@router.get("/onboarding/qr", response_model=OnboardingQrResponse)
def onboarding_qr(_admin: User = Depends(require_admin)) -> OnboardingQrResponse:
    url = get_settings().public_base_url.rstrip("/")
    return OnboardingQrResponse(url=url, payload=url)


@router.post("/admin/scan", response_model=ScanResponse)
def admin_scan(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> ScanResponse:
    stats = scan_library(db)
    return ScanResponse(
        indexed=stats.indexed,
        skipped=stats.skipped,
        removed=stats.removed,
        remuxed=stats.remuxed,
    )


@router.delete("/admin/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media_index(
    media_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    item = db.get(MediaItem, media_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    thumb = resolve_thumbnail(item)
    if thumb is not None:
        thumb.unlink(missing_ok=True)
    db.delete(item)
    db.commit()
