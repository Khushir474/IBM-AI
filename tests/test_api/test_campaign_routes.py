"""Tests for campaign management API routes."""

from unittest.mock import Mock
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.dependencies import get_campaign_service
from src.services.campaign_service import Campaign


class TestChurnCampaignCreateEndpoint:
    """Test POST /api/v1/campaigns/churn"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        app.dependency_overrides[get_campaign_service] = lambda: self.mock_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_campaign_endpoint_create_churn_201(self):
        """Test churn campaign creation."""
        campaign = Campaign(
            campaign_id="camp_123",
            campaign_type="CHURN",
            created_at_iso="2024-06-10T10:00:00Z",
            audience_count=500,
            offer_details={"discount": 15, "type": "email"},
            status="created",
            scheduled_send_time_iso="2024-06-11T10:00:00Z",
        )
        self.mock_service.create_churn_campaign.return_value = campaign

        response = self.client.post(
            "/api/v1/campaigns/churn",
            json={
                "customer_ids": ["cust_1", "cust_2"],
                "intervention_type": "email",
                "offer_details": {"discount": 15},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["campaign_id"] == "camp_123"
        assert data["campaign_type"] == "CHURN"
        assert data["audience_count"] == 500


class TestRecoveryCampaignCreateEndpoint:
    """Test POST /api/v1/campaigns/recovery"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        app.dependency_overrides[get_campaign_service] = lambda: self.mock_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_campaign_endpoint_create_recovery_201(self):
        """Test recovery campaign creation."""
        campaign = Campaign(
            campaign_id="camp_456",
            campaign_type="CART_RECOVERY",
            created_at_iso="2024-06-10T10:00:00Z",
            audience_count=300,
            offer_details={"discount": 10, "free_shipping": True},
            status="created",
            scheduled_send_time_iso=None,
        )
        self.mock_service.create_recovery_campaign.return_value = campaign

        response = self.client.post(
            "/api/v1/campaigns/recovery",
            json={
                "cart_customer_product_pairs": [
                    {"customer_id": "cust_1", "product_id": "prod_1"},
                ],
                "offer_type": "discount",
                "offer_details": {"discount": 10},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["campaign_id"] == "camp_456"
        assert data["campaign_type"] == "CART_RECOVERY"


class TestCampaignGetStatusEndpoint:
    """Test GET /api/v1/campaigns/{campaign_id}"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        app.dependency_overrides[get_campaign_service] = lambda: self.mock_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_campaign_endpoint_get_status_404(self):
        """Test missing campaign returns 404."""
        response = self.client.get("/api/v1/campaigns/missing_id")
        assert response.status_code == 404


class TestCampaignResultsEndpoint:
    """Test GET /api/v1/campaigns/{campaign_id}/results"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        app.dependency_overrides[get_campaign_service] = lambda: self.mock_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_campaign_endpoint_results_404(self):
        """Test missing campaign results returns 404."""
        response = self.client.get("/api/v1/campaigns/missing_id/results")
        assert response.status_code == 404
