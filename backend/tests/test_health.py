"""Tests for health check and basic app configuration."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    """Health check endpoint returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app" in data
    assert "env" in data


def test_api_root():
    """API v1 root endpoint returns welcome message."""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_cors_headers():
    """CORS headers are present for allowed origins."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_request_id_header():
    """Response includes X-Request-ID header."""
    response = client.get("/health")
    assert "x-request-id" in response.headers
