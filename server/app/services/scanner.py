from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.media import MediaItem

logger = logging.getLogger(__name__)

VIDEO_EXT = {".mp4": "video/mp4", ".webm": "video/webm"}
IMAGE_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
THUMB_MAX = 480


@dataclass
class ScanStats:
    indexed: int = 0
    skipped: int = 0
    removed: int = 0
    remuxed: int = 0


def ffmpeg_bin() -> str | None:
    return shutil.which("ffmpeg")


def ffprobe_bin() -> str | None:
    return shutil.which("ffprobe")


def classify(path: Path) -> tuple[str, str] | None:
    ext = path.suffix.lower()
    if ext in VIDEO_EXT:
        return "video", VIDEO_EXT[ext]
    if ext in IMAGE_EXT:
        return "image", IMAGE_EXT[ext]
    return None


def mp4_is_faststart(path: Path) -> bool:
    size = path.stat().st_size
    with path.open("rb") as fh:
        pos = 0
        saw_mdat = False
        while pos + 8 <= size:
            fh.seek(pos)
            header = fh.read(8)
            if len(header) < 8:
                break
            box_size = int.from_bytes(header[:4], "big")
            box_type = header[4:8]
            header_len = 8
            if box_size == 1:
                ext = fh.read(8)
                if len(ext) < 8:
                    break
                box_size = int.from_bytes(ext, "big")
                header_len = 16
            elif box_size == 0:
                box_size = size - pos
            if box_size < header_len:
                break
            if box_type == b"moov":
                return not saw_mdat
            if box_type == b"mdat":
                saw_mdat = True
            pos += box_size
    return False


def remux_faststart(path: Path) -> bool:
    ffmpeg = ffmpeg_bin()
    if ffmpeg is None:
        return False
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False, dir=path.parent) as tmp:
            tmp_path = Path(tmp.name)
        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(path),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        if result.returncode != 0 or not tmp_path.exists() or tmp_path.stat().st_size == 0:
            logger.warning("faststart remux failed for %s: %s", path, result.stderr[-500:])
            if tmp_path.exists():
                tmp_path.unlink()
            return False
        tmp_path.replace(path)
        return True
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("faststart remux error for %s: %s", path, exc)
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()
        return False


def probe_video(path: Path) -> tuple[float | None, int | None, int | None]:
    probe = ffprobe_bin()
    if probe is None:
        return None, None, None
    result = subprocess.run(
        [
            probe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-show_entries",
            "stream=width,height,codec_type",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        return None, None, None
    data = json.loads(result.stdout or "{}")
    duration = None
    try:
        duration = float(data.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        duration = None
    width = height = None
    for stream in data.get("streams") or []:
        if stream.get("codec_type") == "video":
            width = stream.get("width")
            height = stream.get("height")
            break
    return duration, width, height


def make_image_thumbnail(source: Path, dest: Path) -> bool:
    try:
        with Image.open(source) as img:
            img = img.convert("RGB")
            img.thumbnail((THUMB_MAX, THUMB_MAX))
            dest.parent.mkdir(parents=True, exist_ok=True)
            img.save(dest, "JPEG", quality=80)
        return True
    except OSError as exc:
        logger.warning("image thumbnail failed for %s: %s", source, exc)
        return False


def make_video_thumbnail(source: Path, dest: Path, duration: float | None) -> bool:
    ffmpeg = ffmpeg_bin()
    if ffmpeg is None:
        return False
    timestamp = 0.0
    if duration and duration > 1:
        timestamp = duration * 0.1
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-q:v",
            "4",
            str(dest),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return result.returncode == 0 and dest.exists()


def _relative_posix(path: Path) -> str:
    return path.resolve().relative_to(get_settings().library_root.resolve()).as_posix()


def _absolute(item: MediaItem) -> Path:
    return (get_settings().library_root / item.relative_path).resolve()


def scan_library(db: Session) -> ScanStats:
    cfg = get_settings()
    root = cfg.library_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    stats = ScanStats()
    seen: set[str] = set()

    files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() != ".tmp"]
    for path in files:
        try:
            rel = _relative_posix(path)
        except ValueError:
            continue
        seen.add(rel)
        classified = classify(path)
        item = db.scalar(select(MediaItem).where(MediaItem.relative_path == rel))
        mtime_ns = path.stat().st_mtime_ns
        size = path.stat().st_size

        if classified is None:
            stats.skipped += 1
            if item is None:
                item = MediaItem(
                    relative_path=rel,
                    filename=path.name,
                    media_type="unknown",
                    mime_type="application/octet-stream",
                    size_bytes=size,
                    playable=False,
                    skip_reason="unsupported_type",
                    mtime_ns=mtime_ns,
                )
                db.add(item)
            else:
                item.playable = False
                item.skip_reason = "unsupported_type"
                item.size_bytes = size
                item.mtime_ns = mtime_ns
            continue

        media_type, mime = classified
        if item is not None and item.playable and item.mtime_ns == mtime_ns and item.size_bytes == size:
            stats.indexed += 1
            continue

        skip_reason = None
        duration = width = height = None
        remuxed = False

        if media_type == "video" and path.suffix.lower() == ".mp4" and cfg.faststart_remux:
            if not mp4_is_faststart(path):
                if remux_faststart(path):
                    remuxed = True
                    stats.remuxed += 1
                    mtime_ns = path.stat().st_mtime_ns
                    size = path.stat().st_size
                else:
                    skip_reason = "not_faststart"

        if media_type == "video":
            duration, width, height = probe_video(path)
            if ffprobe_bin() is None:
                skip_reason = skip_reason or "ffprobe_missing"
        else:
            try:
                with Image.open(path) as img:
                    width, height = img.size
            except OSError:
                skip_reason = "unreadable_image"

        playable = skip_reason is None
        if item is None:
            item = MediaItem(
                relative_path=rel,
                filename=path.name,
                media_type=media_type,
                mime_type=mime,
                size_bytes=size,
                duration_seconds=duration,
                width=width,
                height=height,
                playable=playable,
                skip_reason=skip_reason,
                mtime_ns=mtime_ns,
            )
            db.add(item)
            db.flush()
        else:
            item.filename = path.name
            item.media_type = media_type
            item.mime_type = mime
            item.size_bytes = size
            item.duration_seconds = duration
            item.width = width
            item.height = height
            item.playable = playable
            item.skip_reason = skip_reason
            item.mtime_ns = mtime_ns
            db.flush()

        if playable:
            thumb = cfg.thumbnail_dir / f"{item.id}.jpg"
            ok = False
            if media_type == "image":
                ok = make_image_thumbnail(path, thumb)
            else:
                ok = make_video_thumbnail(path, thumb, duration)
            item.thumbnail_relpath = f"{item.id}.jpg" if ok else None
            stats.indexed += 1
        else:
            item.thumbnail_relpath = None
            stats.skipped += 1

        if remuxed:
            logger.info("remuxed %s for faststart", rel)

    existing = list(db.scalars(select(MediaItem)).all())
    for item in existing:
        if item.relative_path not in seen:
            thumb = cfg.thumbnail_dir / f"{item.id}.jpg"
            if thumb.exists():
                thumb.unlink()
            db.delete(item)
            stats.removed += 1

    db.commit()
    return stats


def resolve_media_file(item: MediaItem) -> Path:
    path = _absolute(item)
    root = get_settings().library_root.resolve()
    if root not in path.parents and path != root:
        raise ValueError("path escapes library root")
    return path


def resolve_thumbnail(item: MediaItem) -> Path | None:
    if not item.thumbnail_relpath:
        return None
    path = (get_settings().thumbnail_dir / item.thumbnail_relpath).resolve()
    thumb_root = get_settings().thumbnail_dir.resolve()
    if thumb_root not in path.parents and path != thumb_root:
        return None
    return path if path.is_file() else None
