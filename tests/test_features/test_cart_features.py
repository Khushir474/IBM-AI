"""Tests for Task 1.5: Cart Abandonment Feature Engineering."""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock


class TestCartFeatureEngineerImports:
    """Verify cart feature engineer module can be imported."""

    def test_cart_feature_engineer_importable(self):
        """Test that CartAbandonmentFeatureEngineer can be imported."""
        try:
            from src.features.cart_features import CartAbandonmentFeatureEngineer
            assert CartAbandonmentFeatureEngineer is not None
        except ImportError as e:
            pytest.fail(f"Failed to import CartAbandonmentFeatureEngineer: {e}")

    def test_cart_features_schema_importable(self):
        """Test that CartAbandonmentFeatures schema can be imported."""
        try:
            from src.features.cart_features import CartAbandonmentFeatures
            assert CartAbandonmentFeatures is not None
        except ImportError as e:
            pytest.fail(f"Failed to import CartAbandonmentFeatures schema: {e}")


class TestCartFeatureEngineerInitialization:
    """Test CartAbandonmentFeatureEngineer initialization."""

    def test_cart_feature_engineer_initialization(self):
        """Test CartAbandonmentFeatureEngineer can be initialized."""
        from src.features.cart_features import CartAbandonmentFeatureEngineer

        engineer = CartAbandonmentFeatureEngineer(
            customer_dao=MagicMock(),
            cart_dao=MagicMock(),
            session_dao=MagicMock(),
            product_perf_dao=MagicMock(),
        )

        assert engineer is not None


class TestCartFeatureComputation:
    """Test individual cart feature computations."""

    def test_cart_value_computation(self):
        """Test computing cart_value feature."""
        from src.features.cart_features import CartAbandonmentFeatureEngineer

        engineer = CartAbandonmentFeatureEngineer(
            customer_dao=MagicMock(),
            cart_dao=MagicMock(),
            session_dao=MagicMock(),
            product_perf_dao=MagicMock(),
        )

        cart_items = [
            {"unit_price": 50.0, "quantity": 2},  # 100
            {"unit_price": 75.0, "quantity": 1},  # 75
        ]

        value = engineer._compute_cart_value(cart_items)
        assert value == 175.0

    def test_cart_item_count_computation(self):
        """Test computing cart_item_count feature."""
        from src.features.cart_features import CartAbandonmentFeatureEngineer

        engineer = CartAbandonmentFeatureEngineer(
            customer_dao=MagicMock(),
            cart_dao=MagicMock(),
            session_dao=MagicMock(),
            product_perf_dao=MagicMock(),
        )

        cart_items = [
            {"quantity": 2},
            {"quantity": 3},
            {"quantity": 1},
        ]

        count = engineer._compute_cart_item_count(cart_items)
        assert count == 6

    def test_time_since_abandon_computation(self):
        """Test computing time_since_abandon feature."""
        from src.features.cart_features import CartAbandonmentFeatureEngineer

        engineer = CartAbandonmentFeatureEngineer(
            customer_dao=MagicMock(),
            cart_dao=MagicMock(),
            session_dao=MagicMock(),
            product_perf_dao=MagicMock(),
        )

        now = datetime.utcnow()
        abandon_time = now - timedelta(hours=2)

        cart_items = [{"added_at": abandon_time}]

        hours_since = engineer._compute_time_since_abandon(cart_items)
        assert 1.5 <= hours_since <= 2.5  # ~2 hours

    def test_customer_repeat_buyer_feature(self):
        """Test customer_repeat_buyer feature."""
        from src.features.cart_features import CartAbandonmentFeatureEngineer

        engineer = CartAbandonmentFeatureEngineer(
            customer_dao=MagicMock(),
            cart_dao=MagicMock(),
            session_dao=MagicMock(),
            product_perf_dao=MagicMock(),
        )

        # Customer with multiple orders
        is_repeat = engineer._compute_customer_repeat_buyer(5)
        assert is_repeat is True

        # New customer with 1 order
        is_repeat = engineer._compute_customer_repeat_buyer(1)
        assert is_repeat is False


class TestCartFeatureVectorGeneration:
    """Test complete cart feature vector generation."""

    @pytest.mark.asyncio
    async def test_compute_features_complete_vector(self):
        """Test computing complete feature vector for cart abandonment."""
        from src.features.cart_features import CartAbandonmentFeatureEngineer

        customer_id = uuid4()
        product_id = uuid4()

        # Mock DAOs
        customer_dao = AsyncMock()
        customer_dao.get_customer.return_value = {
            "customer_id": str(customer_id),
            "total_orders": 8,
        }

        cart_dao = AsyncMock()
        cart_dao.get_active_carts.return_value = [
            {"product_id": str(product_id), "unit_price": 99.99, "quantity": 2, "added_at": datetime.utcnow() - timedelta(hours=1)},
        ]

        session_dao = AsyncMock()
        session_dao.get_recent_sessions.return_value = [
            {"device_type": "mobile"},
        ]

        product_perf_dao = AsyncMock()
        product_perf_dao.get_weekly_performance.return_value = [
            {"units_sold": 100, "return_rate": 0.05},
        ]

        engineer = CartAbandonmentFeatureEngineer(
            customer_dao=customer_dao,
            cart_dao=cart_dao,
            session_dao=session_dao,
            product_perf_dao=product_perf_dao,
        )

        features = await engineer.compute_features(customer_id, product_id)

        # Verify all 8 features are present
        assert features is not None
        assert hasattr(features, "cart_value")
        assert hasattr(features, "cart_item_count")
        assert hasattr(features, "item_avg_recovery_rate")
        assert hasattr(features, "customer_repeat_buyer")
        assert hasattr(features, "time_since_abandon")
        assert hasattr(features, "previous_abandon_count")
        assert hasattr(features, "shipping_cost_ratio")
        assert hasattr(features, "device_type")

    @pytest.mark.asyncio
    async def test_compute_features_with_missing_data(self):
        """Test feature computation handles missing data gracefully."""
        from src.features.cart_features import CartAbandonmentFeatureEngineer

        customer_id = uuid4()
        product_id = uuid4()

        # Mock DAOs with minimal data
        customer_dao = AsyncMock()
        customer_dao.get_customer.return_value = {
            "customer_id": str(customer_id),
            "total_orders": 0,
        }

        cart_dao = AsyncMock()
        cart_dao.get_active_carts.return_value = []

        session_dao = AsyncMock()
        session_dao.get_recent_sessions.return_value = []

        product_perf_dao = AsyncMock()
        product_perf_dao.get_weekly_performance.return_value = []

        engineer = CartAbandonmentFeatureEngineer(
            customer_dao=customer_dao,
            cart_dao=cart_dao,
            session_dao=session_dao,
            product_perf_dao=product_perf_dao,
        )

        # Should not raise exception
        features = await engineer.compute_features(customer_id, product_id)
        assert features is not None

    @pytest.mark.asyncio
    async def test_compute_features_for_new_customer(self):
        """Test feature computation for new customer (no history)."""
        from src.features.cart_features import CartAbandonmentFeatureEngineer

        customer_id = uuid4()
        product_id = uuid4()

        # New customer with no orders
        customer_dao = AsyncMock()
        customer_dao.get_customer.return_value = {
            "customer_id": str(customer_id),
            "total_orders": 0,
        }

        cart_dao = AsyncMock()
        now = datetime.utcnow()
        cart_dao.get_active_carts.return_value = [
            {"product_id": str(product_id), "unit_price": 50.0, "quantity": 1, "added_at": now - timedelta(hours=3)},
        ]

        session_dao = AsyncMock()
        session_dao.get_recent_sessions.return_value = []

        product_perf_dao = AsyncMock()
        product_perf_dao.get_weekly_performance.return_value = []

        engineer = CartAbandonmentFeatureEngineer(
            customer_dao=customer_dao,
            cart_dao=cart_dao,
            session_dao=session_dao,
            product_perf_dao=product_perf_dao,
        )

        features = await engineer.compute_features(customer_id, product_id)
        assert features is not None
        # New customer should not be marked as repeat buyer
        assert features.customer_repeat_buyer is False


class TestCartFeatureValidation:
    """Test feature validation and data quality checks."""

    def test_feature_value_ranges(self):
        """Test that computed features are within expected ranges."""
        from src.features.cart_features import CartAbandonmentFeatureEngineer

        engineer = CartAbandonmentFeatureEngineer(
            customer_dao=MagicMock(),
            cart_dao=MagicMock(),
            session_dao=MagicMock(),
            product_perf_dao=MagicMock(),
        )

        # Cart value should be non-negative
        value = engineer._compute_cart_value([{"unit_price": 100.0, "quantity": 2}])
        assert value >= 0

        # Item count should be non-negative
        count = engineer._compute_cart_item_count([{"quantity": 5}])
        assert count >= 0

    def test_feature_null_handling(self):
        """Test that features handle null/missing values."""
        from src.features.cart_features import CartAbandonmentFeatureEngineer

        engineer = CartAbandonmentFeatureEngineer(
            customer_dao=MagicMock(),
            cart_dao=MagicMock(),
            session_dao=MagicMock(),
            product_perf_dao=MagicMock(),
        )

        # Empty cart items should not crash
        value = engineer._compute_cart_value([])
        assert value == 0.0

        count = engineer._compute_cart_item_count([])
        assert count == 0


class TestCartFeatureIntegration:
    """Integration tests for cart feature engineering."""

    @pytest.mark.asyncio
    async def test_cart_feature_engineer_full_pipeline(self):
        """Test complete pipeline: cart → DAOs → features."""
        from src.features.cart_features import CartAbandonmentFeatureEngineer

        customer_id = uuid4()
        product_id = uuid4()
        now = datetime.utcnow()

        # Setup realistic mock data
        customer_dao = AsyncMock()
        customer_dao.get_customer.return_value = {
            "customer_id": str(customer_id),
            "total_orders": 12,
            "email": "customer@example.com",
        }

        cart_dao = AsyncMock()
        cart_dao.get_active_carts.return_value = [
            {"product_id": str(product_id), "unit_price": 149.99, "quantity": 2, "added_at": now - timedelta(hours=4)},
            {"product_id": str(uuid4()), "unit_price": 49.99, "quantity": 1, "added_at": now - timedelta(hours=4)},
        ]

        session_dao = AsyncMock()
        session_dao.get_recent_sessions.return_value = [
            {"device_type": "mobile", "created_at": now - timedelta(minutes=30)},
        ]

        product_perf_dao = AsyncMock()
        product_perf_dao.get_weekly_performance.return_value = [
            {"units_sold": 250, "return_rate": 0.08},
        ]

        engineer = CartAbandonmentFeatureEngineer(
            customer_dao=customer_dao,
            cart_dao=cart_dao,
            session_dao=session_dao,
            product_perf_dao=product_perf_dao,
        )

        features = await engineer.compute_features(customer_id, product_id)

        assert features is not None
        assert str(features.customer_id) == str(customer_id)
        assert features.cart_value > 0
        assert features.customer_repeat_buyer is True
        assert features.time_since_abandon >= 4.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
