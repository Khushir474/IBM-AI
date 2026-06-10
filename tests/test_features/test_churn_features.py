"""Tests for Task 1.3: Churn Feature Engineering."""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock


class TestChurnFeatureEngineerImports:
    """Verify churn feature engineer module can be imported."""

    def test_churn_feature_engineer_importable(self):
        """Test that ChurnFeatureEngineer can be imported."""
        try:
            from src.features.churn_features import ChurnFeatureEngineer
            assert ChurnFeatureEngineer is not None
        except ImportError as e:
            pytest.fail(f"Failed to import ChurnFeatureEngineer: {e}")

    def test_churn_features_schema_importable(self):
        """Test that ChurnFeatures schema can be imported."""
        try:
            from src.features.churn_features import ChurnFeatures
            assert ChurnFeatures is not None
        except ImportError as e:
            pytest.fail(f"Failed to import ChurnFeatures schema: {e}")


class TestChurnFeatureEngineerInitialization:
    """Test ChurnFeatureEngineer initialization."""

    def test_churn_feature_engineer_initialization(self):
        """Test ChurnFeatureEngineer can be initialized."""
        from src.features.churn_features import ChurnFeatureEngineer
        from src.data.daos.cassandra_daos import (
            CustomerDAO, OrderDAO, SessionDAO, ReviewDAO
        )

        # Mock DAOs
        customer_dao = MagicMock(spec=CustomerDAO)
        order_dao = MagicMock(spec=OrderDAO)
        session_dao = MagicMock(spec=SessionDAO)
        review_dao = MagicMock(spec=ReviewDAO)

        engineer = ChurnFeatureEngineer(
            customer_dao=customer_dao,
            order_dao=order_dao,
            session_dao=session_dao,
            review_dao=review_dao,
        )

        assert engineer is not None
        assert engineer.customer_dao == customer_dao
        assert engineer.order_dao == order_dao
        assert engineer.session_dao == session_dao
        assert engineer.review_dao == review_dao


class TestChurnFeatureComputation:
    """Test individual churn feature computations."""

    def test_days_since_last_purchase_computation(self):
        """Test computing days_since_last_purchase feature."""
        from src.features.churn_features import ChurnFeatureEngineer

        engineer = ChurnFeatureEngineer(
            customer_dao=MagicMock(),
            order_dao=MagicMock(),
            session_dao=MagicMock(),
            review_dao=MagicMock(),
        )

        # Mock orders with different timestamps
        now = datetime.utcnow()
        last_order_30d_ago = now - timedelta(days=30)
        last_order_60d_ago = now - timedelta(days=60)

        # Should compute days between now and last order
        days_30 = engineer._compute_days_since_last_purchase([
            {"order_date": last_order_30d_ago}
        ])
        assert 29 <= days_30 <= 31  # Allow small time variation

        days_60 = engineer._compute_days_since_last_purchase([
            {"order_date": last_order_60d_ago}
        ])
        assert 59 <= days_60 <= 61

    def test_purchase_frequency_computation(self):
        """Test computing purchase_frequency_30d feature."""
        from src.features.churn_features import ChurnFeatureEngineer

        engineer = ChurnFeatureEngineer(
            customer_dao=MagicMock(),
            order_dao=MagicMock(),
            session_dao=MagicMock(),
            review_dao=MagicMock(),
        )

        now = datetime.utcnow()
        recent_orders = [
            {"order_date": now - timedelta(days=5)},
            {"order_date": now - timedelta(days=10)},
            {"order_date": now - timedelta(days=15)},
        ]

        frequency = engineer._compute_purchase_frequency_30d(recent_orders)
        assert frequency == 3

    def test_average_order_value_computation(self):
        """Test computing average_order_value feature."""
        from src.features.churn_features import ChurnFeatureEngineer

        engineer = ChurnFeatureEngineer(
            customer_dao=MagicMock(),
            order_dao=MagicMock(),
            session_dao=MagicMock(),
            review_dao=MagicMock(),
        )

        order_items = [
            {"unit_price": 100.0, "quantity": 2},  # 200
            {"unit_price": 50.0, "quantity": 1},   # 50
            {"unit_price": 75.0, "quantity": 1},   # 75
        ]

        avg_value = engineer._compute_average_order_value(order_items)
        # (200 + 50 + 75) / 3 = 325 / 3 ≈ 108.33
        assert 108 <= avg_value <= 109

    def test_loyalty_tier_feature(self):
        """Test loyalty_tier feature from customer profile."""
        from src.features.churn_features import ChurnFeatureEngineer

        engineer = ChurnFeatureEngineer(
            customer_dao=MagicMock(),
            order_dao=MagicMock(),
            session_dao=MagicMock(),
            review_dao=MagicMock(),
        )

        customer_gold = {"loyalty_tier": "GOLD"}
        customer_silver = {"loyalty_tier": "SILVER"}
        customer_bronze = {"loyalty_tier": "BRONZE"}

        # Should map loyalty tiers to numeric values
        tier_gold = engineer._compute_loyalty_tier_feature(customer_gold)
        tier_silver = engineer._compute_loyalty_tier_feature(customer_silver)
        tier_bronze = engineer._compute_loyalty_tier_feature(customer_bronze)

        # Higher tier = higher value
        assert tier_gold > tier_silver > tier_bronze


class TestChurnFeatureVectorGeneration:
    """Test complete churn feature vector generation."""

    @pytest.mark.asyncio
    async def test_compute_features_complete_vector(self):
        """Test computing complete feature vector for churn."""
        from src.features.churn_features import ChurnFeatureEngineer

        customer_id = uuid4()

        # Mock DAOs with return values
        customer_dao = AsyncMock()
        customer_dao.get_customer.return_value = {
            "customer_id": str(customer_id),
            "loyalty_tier": "GOLD",
        }

        order_dao = AsyncMock()
        now = datetime.utcnow()
        order_dao.get_inflight_orders.return_value = [
            {"order_date": now - timedelta(days=15), "order_id": "1"},
        ]
        order_dao.get_order_items.return_value = [
            {"unit_price": 100.0, "quantity": 2},
        ]

        session_dao = AsyncMock()
        session_dao.get_recent_sessions.return_value = [
            {"session_id": "s1", "created_at": now - timedelta(days=2)},
            {"session_id": "s2", "created_at": now - timedelta(days=5)},
        ]

        review_dao = AsyncMock()
        review_dao.get_recent_reviews.return_value = []

        engineer = ChurnFeatureEngineer(
            customer_dao=customer_dao,
            order_dao=order_dao,
            session_dao=session_dao,
            review_dao=review_dao,
        )

        features = await engineer.compute_features(customer_id)

        # Verify all 8 features are present
        assert features is not None
        assert hasattr(features, "days_since_last_purchase")
        assert hasattr(features, "purchase_frequency_30d")
        assert hasattr(features, "average_order_value")
        assert hasattr(features, "product_category_affinity")
        assert hasattr(features, "cohort_churn_rate")
        assert hasattr(features, "session_engagement_30d")
        assert hasattr(features, "return_rate")
        assert hasattr(features, "loyalty_tier")

    @pytest.mark.asyncio
    async def test_compute_features_with_missing_data(self):
        """Test feature computation handles missing data gracefully."""
        from src.features.churn_features import ChurnFeatureEngineer

        customer_id = uuid4()

        # Mock DAOs with empty/missing data
        customer_dao = AsyncMock()
        customer_dao.get_customer.return_value = {
            "customer_id": str(customer_id),
            "loyalty_tier": "BRONZE",
        }

        order_dao = AsyncMock()
        order_dao.get_inflight_orders.return_value = []  # No orders
        order_dao.get_order_items.return_value = []

        session_dao = AsyncMock()
        session_dao.get_recent_sessions.return_value = []

        review_dao = AsyncMock()
        review_dao.get_recent_reviews.return_value = []

        engineer = ChurnFeatureEngineer(
            customer_dao=customer_dao,
            order_dao=order_dao,
            session_dao=session_dao,
            review_dao=review_dao,
        )

        # Should not raise exception with missing data
        features = await engineer.compute_features(customer_id)
        assert features is not None

    @pytest.mark.asyncio
    async def test_compute_features_for_new_customer(self):
        """Test feature computation for new customer (no history)."""
        from src.features.churn_features import ChurnFeatureEngineer

        customer_id = uuid4()

        # Mock DAOs - new customer with no history
        customer_dao = AsyncMock()
        customer_dao.get_customer.return_value = {
            "customer_id": str(customer_id),
            "loyalty_tier": "BRONZE",
            "created_at": datetime.utcnow(),
        }

        order_dao = AsyncMock()
        order_dao.get_inflight_orders.return_value = []
        order_dao.get_order_items.return_value = []

        session_dao = AsyncMock()
        session_dao.get_recent_sessions.return_value = []

        review_dao = AsyncMock()
        review_dao.get_recent_reviews.return_value = []

        engineer = ChurnFeatureEngineer(
            customer_dao=customer_dao,
            order_dao=order_dao,
            session_dao=session_dao,
            review_dao=review_dao,
        )

        # Should use sensible defaults for new customers
        features = await engineer.compute_features(customer_id)
        assert features is not None
        # New customer should have high days_since_last_purchase (no purchases)
        assert features.days_since_last_purchase > 0


class TestChurnFeatureValidation:
    """Test feature validation and data quality checks."""

    def test_feature_value_ranges(self):
        """Test that computed features are within expected ranges."""
        from src.features.churn_features import ChurnFeatureEngineer

        engineer = ChurnFeatureEngineer(
            customer_dao=MagicMock(),
            order_dao=MagicMock(),
            session_dao=MagicMock(),
            review_dao=MagicMock(),
        )

        # Loyalty tier should be numeric
        tier = engineer._compute_loyalty_tier_feature({"loyalty_tier": "GOLD"})
        assert 0 <= tier <= 1  # Or whatever range is chosen

    def test_feature_null_handling(self):
        """Test that features handle null/missing values."""
        from src.features.churn_features import ChurnFeatureEngineer

        engineer = ChurnFeatureEngineer(
            customer_dao=MagicMock(),
            order_dao=MagicMock(),
            session_dao=MagicMock(),
            review_dao=MagicMock(),
        )

        # Empty list should not crash
        frequency = engineer._compute_purchase_frequency_30d([])
        assert frequency == 0

        avg_value = engineer._compute_average_order_value([])
        assert avg_value == 0


class TestChurnFeatureIntegration:
    """Integration tests for churn feature engineering."""

    @pytest.mark.asyncio
    async def test_churn_feature_engineer_full_pipeline(self):
        """Test complete pipeline: customer → DAOs → features."""
        from src.features.churn_features import ChurnFeatureEngineer

        customer_id = uuid4()
        now = datetime.utcnow()

        # Setup mock DAOs with realistic data
        customer_dao = AsyncMock()
        customer_dao.get_customer.return_value = {
            "customer_id": str(customer_id),
            "loyalty_tier": "GOLD",
            "email": "customer@example.com",
        }

        order_dao = AsyncMock()
        order_dao.get_inflight_orders.return_value = [
            {"order_date": now - timedelta(days=20), "order_id": "order-1"},
            {"order_date": now - timedelta(days=45), "order_id": "order-2"},
        ]
        order_dao.get_order_items.return_value = [
            {"unit_price": 99.99, "quantity": 1},
            {"unit_price": 149.99, "quantity": 2},
        ]

        session_dao = AsyncMock()
        session_dao.get_recent_sessions.return_value = [
            {"session_id": "s1", "created_at": now - timedelta(days=1)},
            {"session_id": "s2", "created_at": now - timedelta(days=3)},
            {"session_id": "s3", "created_at": now - timedelta(days=7)},
        ]

        review_dao = AsyncMock()
        review_dao.get_recent_reviews.return_value = []

        engineer = ChurnFeatureEngineer(
            customer_dao=customer_dao,
            order_dao=order_dao,
            session_dao=session_dao,
            review_dao=review_dao,
        )

        # Compute features
        features = await engineer.compute_features(customer_id)

        # Verify result is valid feature object
        assert features is not None
        assert str(features.customer_id) == str(customer_id)

        # Verify all DAOs were called appropriately
        customer_dao.get_customer.assert_called_once()
        order_dao.get_inflight_orders.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
