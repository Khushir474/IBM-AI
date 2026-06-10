"""Tests for system health and readiness routes."""

from fastapi.testclient import TestClient
from src.api.main import app


class TestHealthCheckEndpoint:
    """Test GET /health"""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)

    def test_health_check_200(self):
        """Test health check returns healthy status."""
        response = self.client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data
        assert "details" in data
        assert data["details"]["cassandra"] == "ok"
        assert data["details"]["presto"] == "ok"


class TestReadinessCheckEndpoint:
    """Test GET /readiness"""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)

    def test_readiness_check_200(self):
        """Test readiness check returns ready status."""
        response = self.client.get("/readiness")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "version" in data
        assert "timestamp" in data
