"""Tests for churn prediction API routes."""

from unittest.mock import Mock
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.dependencies import get_churn_service
from src.services.churn_service import (
    ChurnRiskScore,
    ChurnTier,
    ChurnIntervention,
)


class TestChurnRiskScoreEndpoint:
    """Test GET /api/v1/churn/customer/{customer_id}/risk-score"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        app.dependency_overrides[get_churn_service] = lambda: self.mock_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_churn_endpoint_risk_score_200(self):
        """Test successful churn risk score retrieval."""
        risk_score = ChurnRiskScore(
            customer_id="cust_123",
            score=75.0,
            tier=ChurnTier.HIGH,
            factors=[
                {"factor": "No purchase in 60 days", "contribution_score": 0.4, "description": "Low activity"},
            ],
            recommended_intervention=ChurnIntervention(
                intervention_type="email",
                description="Send personalized offer",
                recommended_discount=15.0,
                confidence=0.85,
            ),
            confidence=0.85,
        )
        self.mock_service.score_customer.return_value = risk_score

        response = self.client.get("/api/v1/churn/customer/cust_123/risk-score")

        assert response.status_code == 200
        data = response.json()
        assert data["customer_id"] == "cust_123"
        assert data["score"] == 75.0
        assert data["tier"] == "HIGH"
        assert len(data["factors"]) == 1
        assert data["confidence"] == 0.85

    def test_churn_endpoint_not_found_404(self):
        """Test missing customer returns 404."""
        self.mock_service.score_customer.return_value = None

        response = self.client.get("/api/v1/churn/customer/missing/risk-score")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestChurnListByTierEndpoint:
    """Test GET /api/v1/churn/customers"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        app.dependency_overrides[get_churn_service] = lambda: self.mock_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_churn_endpoint_list_pagination(self):
        """Test pagination params work correctly."""
        scores = [
            ChurnRiskScore(
                customer_id=f"cust_{i}",
                score=70 + i,
                tier=ChurnTier.HIGH,
                factors=[],
                recommended_intervention=ChurnIntervention(
                    intervention_type="email",
                    description="Offer",
                    recommended_discount=10.0,
                    confidence=0.8,
                ),
                confidence=0.8,
            )
            for i in range(3)
        ]
        self.mock_service.list_by_tier.return_value = (scores, 100)

        response = self.client.get(
            "/api/v1/churn/customers?churn_tier=HIGH&limit=3&offset=0"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 100
        assert data["limit"] == 3
        assert data["offset"] == 0

    def test_churn_endpoint_invalid_tier_400(self):
        """Test invalid tier param returns 400."""
        response = self.client.get("/api/v1/churn/customers?churn_tier=INVALID")

        assert response.status_code == 400
        assert "Invalid" in response.json()["detail"]


class TestChurnFactorsEndpoint:
    """Test GET /api/v1/churn/customer/{customer_id}/factors"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        app.dependency_overrides[get_churn_service] = lambda: self.mock_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_churn_endpoint_factors_200(self):
        """Test factors endpoint returns list."""
        factors = [
            {"factor": "No purchase in 60 days", "contribution_score": 0.5, "description": "Inactivity"},
            {"factor": "Low LTV", "contribution_score": 0.3, "description": "Low value"},
        ]
        score = ChurnRiskScore(
            customer_id="cust_123",
            score=75.0,
            tier=ChurnTier.HIGH,
            factors=factors,
            recommended_intervention=ChurnIntervention(
                intervention_type="email",
                description="Offer",
                recommended_discount=15.0,
                confidence=0.85,
            ),
            confidence=0.85,
        )
        self.mock_service.score_customer.return_value = score

        response = self.client.get("/api/v1/churn/customer/cust_123/factors")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["factor"] == "No purchase in 60 days"
        assert data[1]["factor"] == "Low LTV"
