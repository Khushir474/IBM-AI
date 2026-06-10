"""Tests for cart abandonment API routes."""

from unittest.mock import Mock
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.dependencies import get_cart_service
from src.services.cart_service import (
    AbandonedCart,
    RecoveryTier,
    RecoveryOfferRecommendation,
)


class TestAbandonedCartsEndpoint:
    """Test GET /api/v1/carts/abandoned"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        app.dependency_overrides[get_cart_service] = lambda: self.mock_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_cart_endpoint_list_abandoned_200(self):
        """Test abandoned carts listing."""
        carts = [
            AbandonedCart(
                customer_id="cust_123",
                product_id="prod_456",
                cart_value=150.0,
                item_count=2,
                abandon_time_iso="2024-06-10T10:00:00Z",
                recovery_score=85.0,
                recovery_tier=RecoveryTier.HIGH,
                factors=[
                    {"factor": "High value cart", "contribution_score": 0.6, "description": "Cart >$100"}
                ],
                recommended_offer=RecoveryOfferRecommendation(
                    offer_type="discount",
                    discount_pct=15.0,
                    free_shipping=False,
                    conversion_probability=0.75,
                ),
            ),
        ]
        self.mock_service.detect_abandoned_carts.return_value = carts

        response = self.client.get("/api/v1/carts/abandoned")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["customer_id"] == "cust_123"
        assert data[0]["recovery_tier"] == "HIGH"


class TestAbandonmentDetailsEndpoint:
    """Test GET /api/v1/carts/{customer_id}/{product_id}/abandonment"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        app.dependency_overrides[get_cart_service] = lambda: self.mock_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_cart_endpoint_abandonment_details_200(self):
        """Test abandonment details retrieval."""
        cart = AbandonedCart(
            customer_id="cust_123",
            product_id="prod_456",
            cart_value=150.0,
            item_count=2,
            abandon_time_iso="2024-06-10T10:00:00Z",
            recovery_score=85.0,
            recovery_tier=RecoveryTier.HIGH,
            factors=[],
            recommended_offer=None,
        )
        self.mock_service.detect_abandoned_carts.return_value = [cart]

        response = self.client.get("/api/v1/carts/cust_123/prod_456/abandonment")

        assert response.status_code == 200
        data = response.json()
        assert data["customer_id"] == "cust_123"
        assert data["cart_value"] == 150.0


class TestRecoveryOfferEndpoint:
    """Test GET /api/v1/carts/{customer_id}/{product_id}/recovery-offer"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        app.dependency_overrides[get_cart_service] = lambda: self.mock_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_cart_endpoint_recovery_offer_200(self):
        """Test recovery offer recommendation."""
        offer = RecoveryOfferRecommendation(
            offer_type="discount",
            discount_pct=15.0,
            free_shipping=False,
            conversion_probability=0.75,
        )
        self.mock_service.recommend_recovery_offer.return_value = offer

        response = self.client.get(
            "/api/v1/carts/cust_123/prod_456/recovery-offer"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["discount_pct"] == 15.0
        assert data["conversion_probability"] == 0.75
