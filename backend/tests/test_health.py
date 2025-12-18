"""
Health endpoint tests
"""

import pytest
from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient):
    """Test /health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_ready_endpoint(client: TestClient):
    """Test /ready endpoint"""
    response = client.get("/ready")
    assert response.status_code in [200, 503]  # 503 if DB/Redis not available
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "redis" in data


def test_trace_id_in_error_response(client: TestClient):
    """Test that trace_id exists in error responses"""
    response = client.get("/nonexistent-endpoint")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "trace_id" in data["error"]
    assert data["error"]["trace_id"] is not None
    # Check that trace_id is also in response header
    assert "X-Trace-ID" in response.headers



