"""Tests for pricing and experiment API routes."""

from unittest.mock import Mock
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.dependencies import get_pricing_service, get_experiment_service
from src.services.pricing_service import PriceRecommendation
from src.services.experiment_service import Experiment, ExperimentResults


class TestPricingRecommendationEndpoint:
    """Test GET /api/v1/pricing/products/{product_id}/recommendation"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        app.dependency_overrides[get_pricing_service] = lambda: self.mock_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_pricing_endpoint_recommendation_200(self):
        """Test price recommendation retrieval."""
        rec = PriceRecommendation(
            product_id="prod_123",
            current_price=100.0,
            recommended_price=85.0,
            discount_pct=15.0,
            expected_revenue_impact=5000.0,
            margin_impact=-2.0,
            confidence=0.85,
            reason="High abandonment rate",
        )
        self.mock_service.recommend_price.return_value = rec

        response = self.client.get("/api/v1/pricing/products/prod_123/recommendation")

        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == "prod_123"
        assert data["discount_pct"] == 15.0
        assert data["expected_revenue_impact"] == 5000.0


class TestExperimentCreateEndpoint:
    """Test POST /api/v1/pricing/experiments"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        app.dependency_overrides[get_experiment_service] = lambda: self.mock_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_experiment_endpoint_create_201(self):
        """Test experiment creation."""
        exp = Experiment(
            experiment_id="exp_789",
            name="Discount A/B Test",
            treatments=[{"name": "10% discount"}, {"name": "15% discount"}],
            metric="recovery_rate",
            start_date_iso="2024-06-10T00:00:00Z",
            end_date_iso="2024-06-17T00:00:00Z",
            status="active",
            sample_size_per_treatment=1000,
        )
        self.mock_service.create_discount_experiment.return_value = exp

        response = self.client.post(
            "/api/v1/pricing/experiments",
            json={
                "name": "Discount A/B Test",
                "treatments": [{"name": "10% discount"}, {"name": "15% discount"}],
                "metric": "recovery_rate",
                "start_date_iso": "2024-06-10T00:00:00Z",
                "end_date_iso": "2024-06-17T00:00:00Z",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["experiment_id"] == "exp_789"
        assert data["status"] == "active"


class TestExperimentResultsEndpoint:
    """Test GET /api/v1/pricing/experiments/{experiment_id}/results"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        app.dependency_overrides[get_experiment_service] = lambda: self.mock_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_experiment_endpoint_results_200(self):
        """Test experiment results retrieval."""
        results = ExperimentResults(
            experiment_id="exp_789",
            treatment_results=[
                {
                    "treatment_name": "10% discount",
                    "conversion_rate": 0.18,
                    "sample_size": 1000,
                },
                {
                    "treatment_name": "15% discount",
                    "conversion_rate": 0.22,
                    "sample_size": 1000,
                },
            ],
            winner="15% discount",
            p_value=0.025,
            significant_at_95=True,
            recommendation="Apply 15% discount",
        )
        self.mock_service.analyze_experiment_results.return_value = results

        response = self.client.get(
            "/api/v1/pricing/experiments/exp_789/results"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["significant_at_95"] is True
        assert data["winner"] == "15% discount"
