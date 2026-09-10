from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.routers import admin, auth, library, media
from app.schemas import HealthResponse
from app.services.auth import bootstrap_admin_if_needed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _scan_loop() -> None:
    interval = get_settings().scan_interval_seconds
    if interval <= 0:
        return
    from app.services.scanner import scan_library

    while True:
        await asyncio.sleep(interval)
        db = SessionLocal()
        try:
            stats = scan_library(db)
            logger.info("periodic scan: %s", stats)
        except Exception:
            logger.exception("periodic scan failed")
        finally:
            db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        bootstrap_admin_if_needed(db)
    finally:
        db.close()
    task = asyncio.create_task(_scan_loop())
    yield
    task.cancel()


app = FastAPI(title="Homemade Streaming Service", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(library.router)
app.include_router(media.router)
app.include_router(admin.router)


@app.get("/api/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()
