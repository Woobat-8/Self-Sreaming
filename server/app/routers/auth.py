from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import create_access_token
from app.models.user import User
from app.schemas import LoginRequest, LogoutRequest, RefreshRequest, TokenResponse
from app.services.auth import authenticate, get_valid_refresh, issue_refresh_token, revoke_refresh

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate(db, body.username, body.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(
        access_token=create_access_token(user),
        refresh_token=issue_refresh_token(db, user),
        expires_in=get_settings().access_token_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    record = get_valid_refresh(db, body.refresh_token)
    if record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user = db.get(User, record.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    revoke_refresh(db, record)
    return TokenResponse(
        access_token=create_access_token(user),
        refresh_token=issue_refresh_token(db, user),
        expires_in=get_settings().access_token_minutes * 60,
    )


@router.post("/logout")
def logout(body: LogoutRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    record = get_valid_refresh(db, body.refresh_token)
    if record is not None:
        revoke_refresh(db, record)
    return {"status": "ok"}
