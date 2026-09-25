from __future__ import annotations

from pathlib import Path

from fastapi.responses import FileResponse


def file_response(
    path: Path,
    media_type: str,
    *,
    as_attachment: bool = False,
    filename: str | None = None,
) -> FileResponse:
    headers = {"Accept-Ranges": "bytes"}
    return FileResponse(
        path,
        media_type=media_type,
        filename=filename if as_attachment else None,
        content_disposition_type="attachment" if as_attachment else "inline",
        headers=headers,
    )
