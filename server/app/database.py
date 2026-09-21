from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


engine = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False)


def configure_engine():
    global engine
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    settings.thumbnail_dir.mkdir(parents=True, exist_ok=True)
    settings.library_root.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
    )
    SessionLocal.configure(bind=engine)
    return engine


def get_db() -> Session:
    if engine is None:
        configure_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import media, refresh_token, user  # noqa: F401

    configure_engine()
    Base.metadata.create_all(bind=engine)


def reset_engine() -> None:
    global engine
    if engine is not None:
        engine.dispose()
    engine = None
    SessionLocal.configure(bind=None)
