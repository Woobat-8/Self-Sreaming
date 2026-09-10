from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    jwt_secret: str = "change-me-jwt-secret"
    media_signing_secret: str = "change-me-media-signing-secret"
    public_base_url: str = "http://127.0.0.1:8080"

    data_dir: Path = Path("./data")
    library_root: Path = Path("./library")

    bootstrap_admin_user: str = ""
    bootstrap_admin_password: str = ""

    faststart_remux: bool = True
    access_token_minutes: int = 30
    refresh_token_days: int = 30
    signed_url_hours: int = 6
    scan_interval_seconds: int = 0

    cors_allow_origins: str = "*"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "db" / "media.sqlite3"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path.as_posix()}"

    @property
    def thumbnail_dir(self) -> Path:
        return self.data_dir / "cache" / "thumbnails"

    @property
    def cors_origins(self) -> list[str]:
        raw = self.cors_allow_origins.strip()
        if raw == "*":
            return ["*"]
        return [part.strip() for part in raw.split(",") if part.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
