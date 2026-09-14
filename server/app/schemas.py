from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class MediaUrls(BaseModel):
    stream: str
    download: str
    thumbnail: str | None = None


class MediaItemOut(BaseModel):
    id: str
    filename: str
    type: str
    mime_type: str
    size_bytes: int
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    urls: MediaUrls


class LibraryResponse(BaseModel):
    items: list[MediaItemOut]
    page: int
    page_size: int
    total: int


class ScanResponse(BaseModel):
    indexed: int
    skipped: int
    removed: int
    remuxed: int


class OnboardingQrResponse(BaseModel):
    url: str
    payload: str = Field(description="Value to encode in the household QR code")


class HealthResponse(BaseModel):
    status: str = "ok"
