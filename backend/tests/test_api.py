import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_dashboard_stats():
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_active_jobs" in data
    assert "sponsorship_breakdown" in data
    assert "top_skills" in data

def test_get_jobs_endpoint():
    response = client.get("/api/jobs?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert "total_pages" in data

def test_get_jobs_with_senior_experience_level():
    response = client.get("/api/jobs?experience_level=senior&page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data


def test_sponsorship_lookup_endpoint():
    response = client.get("/api/sponsorship/lookup?company=Monzo+Bank")
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is True
    assert data["status"] == "LICENSED"


def test_auth_login_admin_success():
    from backend.app.database.config import settings
    response = client.post(
        "/api/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["role"] == "ADMIN"
    assert "token" in data

    token = data["token"]
    # Check /api/auth/me with Bearer token
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["authenticated"] is True
    assert me_resp.json()["role"] == "ADMIN"


def test_auth_login_invalid_credentials():
    response = client.post(
        "/api/auth/login",
        json={"username": "random_user", "password": "wrongpassword"}
    )
    assert response.status_code == 401

