import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.utils.rate_limiter import limiter, SlidingWindowRateLimiter

client = TestClient(app)

def test_rate_limiter_unit():
    test_limiter = SlidingWindowRateLimiter()
    key = "unit_test_ip"
    max_req = 5
    window = 10

    # First 5 should succeed
    for i in range(max_req):
        allowed, remaining, retry_after = test_limiter.check_rate_limit(key, max_req, window)
        assert allowed is True
        assert remaining == max_req - (i + 1)
        assert retry_after == 0

    # 6th should fail with 429 logic
    allowed, remaining, retry_after = test_limiter.check_rate_limit(key, max_req, window)
    assert allowed is False
    assert remaining == 0
    assert retry_after > 0


def test_rate_limit_headers():
    limiter.requests.clear()
    response = client.get("/api/jobs?page=1&page_size=1")
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers


def test_login_rate_limiting():
    limiter.requests.clear()
    # 10 allowed per minute
    for _ in range(10):
        resp = client.post("/api/auth/login", json={"username": "bad", "password": "wrong"})
        assert resp.status_code == 401

    # 11th should be rate-limited (HTTP 429)
    resp_blocked = client.post("/api/auth/login", json={"username": "bad", "password": "wrong"})
    assert resp_blocked.status_code == 429
    assert "Too many requests" in resp_blocked.json()["detail"]
    assert "Retry-After" in resp_blocked.headers

    # Reset limiter after test
    limiter.requests.clear()


def test_health_check_exempt_from_rate_limit():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
