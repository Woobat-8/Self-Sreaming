from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import reset_engine


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LIBRARY_ROOT", str(tmp_path / "library"))
    monkeypatch.setenv("JWT_SECRET", "unit-test-jwt-secret-key-32bytes!!")
    monkeypatch.setenv("MEDIA_SIGNING_SECRET", "unit-test-media-signing-key-32b!")
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://testserver")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_USER", "admin")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "adminpass")
    monkeypatch.setenv("FASTSTART_REMUX", "false")
    get_settings.cache_clear()
    reset_engine()
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
    reset_engine()
    get_settings.cache_clear()


@pytest.fixture()
def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "adminpass"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
