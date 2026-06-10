"""Tests for LTV prediction API routes."""

from unittest.mock import Mock
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.dependencies import get_ltv_service
from src.services.ltv_service import (
    LTVPredictions,
    LTVCohort,
    HighPotentialCustomer,
    ModelAccuracyMetrics,
)


class TestLTVPredictionsEndpoint:
    """Test GET /api/v1/ltv/customer/{customer_id}/predictions"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        app.dependency_overrides[get_ltv_service] = lambda: self.mock_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_ltv_endpoint_predictions_200(self):
        """Test LTV predictions retrieval."""
        predictions = LTVPredictions(
            customer_id="cust_123",
            ltv_7day=50.0,
            ltv_30day=200.0,
            ltv_90day=500.0,
            ltv_365day=1500.0,
            factors=[
                {"factor": "High frequency", "contribution_score": 0.6, "description": "Frequent buyer"},
            ],
        )
        self.mock_service.predict_ltv.return_value = predictions

        response = self.client.get("/api/v1/ltv/customer/cust_123/predictions")

        assert response.status_code == 200
        data = response.json()
        assert data["customer_id"] == "cust_123"
        assert data["ltv_90day"] == 500.0
        assert data["ltv_365day"] == 1500.0

    def test_ltv_endpoint_not_found_404(self):
        """Test missing customer returns 404."""
        self.mock_service.predict_ltv.return_value = None

        response = self.client.get("/api/v1/ltv/customer/missing/predictions")

        assert response.status_code == 404


class TestLTVCohortsEndpoint:
    """Test GET /api/v1/ltv/cohorts/high-value"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        app.dependency_overrides[get_ltv_service] = lambda: self.mock_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_ltv_endpoint_cohorts_200(self):
        """Test high-value cohorts listing."""
        cohorts = [
            LTVCohort(
                cohort_name="Premium Customers",
                size=500,
                avg_ltv=2000.0,
                avg_ltv_7day=100.0,
                avg_ltv_30day=400.0,
                avg_ltv_90day=1000.0,
                avg_ltv_365day=2000.0,
                characteristics={"region": "US", "category": "Electronics"},
            ),
        ]
        self.mock_service.list_high_value_cohorts.return_value = cohorts

        response = self.client.get("/api/v1/ltv/cohorts/high-value")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["cohort_name"] == "Premium Customers"
        assert data[0]["avg_ltv"] == 2000.0


class TestLTVHighPotentialEndpoint:
    """Test GET /api/v1/ltv/customers/new-high-potential"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        app.dependency_overrides[get_ltv_service] = lambda: self.mock_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_ltv_endpoint_new_potential_200(self):
        """Test new high-potential customers listing."""
        customers = [
            HighPotentialCustomer(
                customer_id="cust_456",
                days_as_customer=3,
                predicted_ltv_90day=300.0,
                confidence=0.9,
                signals=["high_first_order", "repeat_purchase"],
            ),
        ]
        self.mock_service.flag_new_high_potential.return_value = customers

        response = self.client.get("/api/v1/ltv/customers/new-high-potential")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["predicted_ltv_90day"] == 300.0
