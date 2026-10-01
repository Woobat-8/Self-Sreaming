from __future__ import annotations

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.services.auth import create_user


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_success(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "adminpass"})
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_login_failure(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401


def test_library_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/library")
    assert response.status_code == 401


def test_refresh_and_logout(client: TestClient) -> None:
    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "adminpass"}).json()
    refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert refresh.status_code == 200
    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert reused.status_code == 401
    logout = client.post("/api/v1/auth/logout", json={"refresh_token": refresh.json()["refresh_token"]})
    assert logout.status_code == 200
    after = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh.json()["refresh_token"]})
    assert after.status_code == 401


def test_member_cannot_scan(client: TestClient) -> None:
    db = SessionLocal()
    try:
        create_user(db, "member", "memberpass", role="member")
    finally:
        db.close()
    login = client.post("/api/v1/auth/login", json={"username": "member", "password": "memberpass"})
    token = login.json()["access_token"]
    response = client.post("/api/v1/admin/scan", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
