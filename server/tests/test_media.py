from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from PIL import Image

from app.config import get_settings
from app.services.signed_urls import mint_media_token


def _write_jpeg(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 48), color=(20, 80, 160)).save(path, "JPEG")


def test_scan_indexes_jpeg_skips_txt(client: TestClient, admin_headers: dict[str, str]) -> None:
    root = get_settings().library_root
    _write_jpeg(root / "shared" / "images" / "cat.jpg")
    (root / "shared" / "images" / "notes.txt").write_text("nope", encoding="utf-8")

    scan = client.post("/api/v1/admin/scan", headers=admin_headers)
    assert scan.status_code == 200, scan.text
    body = scan.json()
    assert body["indexed"] == 1
    assert body["skipped"] >= 1

    listing = client.get("/api/v1/library", headers=admin_headers)
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert len(items) == 1
    assert items[0]["filename"] == "cat.jpg"
    assert items[0]["type"] == "image"


def test_stream_requires_matching_signed_url(client: TestClient, admin_headers: dict[str, str]) -> None:
    root = get_settings().library_root
    _write_jpeg(root / "shared" / "images" / "cat.jpg")
    client.post("/api/v1/admin/scan", headers=admin_headers)
    item = client.get("/api/v1/library", headers=admin_headers).json()["items"][0]
    media_id = item["id"]

    missing = client.get(f"/api/v1/media/{media_id}/stream")
    assert missing.status_code == 401

    download_token = mint_media_token(media_id, "download")
    wrong = client.get(f"/api/v1/media/{media_id}/stream", params={"token": download_token})
    assert wrong.status_code == 401

    stream_url = item["urls"]["stream"]
    parsed = urlparse(stream_url)
    token = parse_qs(parsed.query)["token"][0]
    ok = client.get(parsed.path, params={"token": token})
    assert ok.status_code == 200
    assert ok.headers["content-type"].startswith("image/jpeg")
    assert "accept-ranges" in {k.lower() for k in ok.headers.keys()}


def test_range_request(client: TestClient, admin_headers: dict[str, str]) -> None:
    root = get_settings().library_root
    _write_jpeg(root / "shared" / "images" / "cat.jpg")
    client.post("/api/v1/admin/scan", headers=admin_headers)
    item = client.get("/api/v1/library", headers=admin_headers).json()["items"][0]
    parsed = urlparse(item["urls"]["stream"])
    token = parse_qs(parsed.query)["token"][0]
    response = client.get(parsed.path, params={"token": token}, headers={"Range": "bytes=0-10"})
    assert response.status_code == 206
    assert response.headers["content-range"].startswith("bytes 0-10/")
    assert len(response.content) == 11


def test_download_disposition(client: TestClient, admin_headers: dict[str, str]) -> None:
    root = get_settings().library_root
    _write_jpeg(root / "shared" / "images" / "cat.jpg")
    client.post("/api/v1/admin/scan", headers=admin_headers)
    item = client.get("/api/v1/library", headers=admin_headers).json()["items"][0]
    parsed = urlparse(item["urls"]["download"])
    token = parse_qs(parsed.query)["token"][0]
    response = client.get(parsed.path, params={"token": token})
    assert response.status_code == 200
    assert "attachment" in response.headers.get("content-disposition", "")


def test_onboarding_qr_admin_only(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/onboarding/qr", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["url"] == "http://testserver"
