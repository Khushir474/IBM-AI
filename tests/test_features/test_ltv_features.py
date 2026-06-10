"""Tests for Task 1.4: LTV Feature Engineering."""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock


class TestLTVFeatureEngineerImports:
    """Verify LTV feature engineer module can be imported."""

    def test_ltv_feature_engineer_importable(self):
        """Test that LTVFeatureEngineer can be imported."""
        try:
            from src.features.ltv_features import LTVFeatureEngineer
            assert LTVFeatureEngineer is not None
        except ImportError as e:
            pytest.fail(f"Failed to import LTVFeatureEngineer: {e}")

    def test_ltv_features_schema_importable(self):
        """Test that LTVFeatures schema can be imported."""
        try:
            from src.features.ltv_features import LTVFeatures
            assert LTVFeatures is not None
        except ImportError as e:
            pytest.fail(f"Failed to import LTVFeatures schema: {e}")


class TestLTVFeatureEngineerInitialization:
    """Test LTVFeatureEngineer initialization."""

    def test_ltv_feature_engineer_initialization(self):
        """Test LTVFeatureEngineer can be initialized."""
        from src.features.ltv_features import LTVFeatureEngineer

        engineer = LTVFeatureEngineer(
            customer_dao=MagicMock(),
            order_dao=MagicMock(),
            customer_ltv_dao=MagicMock(),
            daily_sales_dao=MagicMock(),
        )

        assert engineer is not None


class TestLTVFeatureComputation:
    """Test individual LTV feature computations."""

    def test_historical_ltv_computation(self):
        """Test computing historical_ltv feature."""
        from src.features.ltv_features import LTVFeatureEngineer

        engineer = LTVFeatureEngineer(
            customer_dao=MagicMock(),
            order_dao=MagicMock(),
            customer_ltv_dao=MagicMock(),
            daily_sales_dao=MagicMock(),
        )

        customer = {"current_ltv": 1500.50}
        ltv = engineer._compute_historical_ltv(customer)
        assert ltv == 1500.50

    def test_cumulative_orders_computation(self):
        """Test computing cumulative_orders feature."""
        from src.features.ltv_features import LTVFeatureEngineer

        engineer = LTVFeatureEngineer(
            customer_dao=MagicMock(),
            order_dao=MagicMock(),
            customer_ltv_dao=MagicMock(),
            daily_sales_dao=MagicMock(),
        )

        customer = {"total_orders": 25}
        orders = engineer._compute_cumulative_orders(customer)
        assert orders == 25

    def test_repeat_purchase_rate_computation(self):
        """Test computing repeat_purchase_rate feature."""
        from src.features.ltv_features import LTVFeatureEngineer

        engineer = LTVFeatureEngineer(
            customer_dao=MagicMock(),
            order_dao=MagicMock(),
            customer_ltv_dao=MagicMock(),
            daily_sales_dao=MagicMock(),
        )

        # Customer with 10 orders, 7 have multiple items
        rate = engineer._compute_repeat_purchase_rate(10, 7)
        assert 0.7 == rate


class TestLTVFeatureVectorGeneration:
    """Test complete LTV feature vector generation."""

    @pytest.mark.asyncio
    async def test_compute_features_complete_vector(self):
        """Test computing complete feature vector for LTV."""
        from src.features.ltv_features import LTVFeatureEngineer

        customer_id = uuid4()

        # Mock DAOs
        customer_dao = AsyncMock()
        customer_dao.get_customer.return_value = {
            "customer_id": str(customer_id),
            "current_ltv": 2500.0,
            "total_orders": 35,
            "loyalty_tier": "GOLD",
            "acquired_at": datetime.utcnow() - timedelta(days=180),
        }

        order_dao = AsyncMock()
        order_dao.get_inflight_orders.return_value = []

        customer_ltv_dao = AsyncMock()
        customer_ltv_dao.get_latest_customer_ltv.return_value = {
            "ltv": 2300.0,
            "cumulative_orders": 32,
        }

        daily_sales_dao = AsyncMock()
        daily_sales_dao.get_daily_revenue.return_value = []

        engineer = LTVFeatureEngineer(
            customer_dao=customer_dao,
            order_dao=order_dao,
            customer_ltv_dao=customer_ltv_dao,
            daily_sales_dao=daily_sales_dao,
        )

        features = await engineer.compute_features(customer_id)

        # Verify all 7 features are present
        assert features is not None
        assert hasattr(features, "historical_ltv")
        assert hasattr(features, "cohort_avg_ltv")
        assert hasattr(features, "cumulative_orders")
        assert hasattr(features, "product_category_spend")
        assert hasattr(features, "repeat_purchase_rate")
        assert hasattr(features, "seasonality_index")
        assert hasattr(features, "loyalty_tier")

    @pytest.mark.asyncio
    async def test_compute_features_with_missing_data(self):
        """Test feature computation handles missing data gracefully."""
        from src.features.ltv_features import LTVFeatureEngineer

        customer_id = uuid4()

        # Mock DAOs with minimal data
        customer_dao = AsyncMock()
        customer_dao.get_customer.return_value = {
            "customer_id": str(customer_id),
            "loyalty_tier": "BRONZE",
        }

        order_dao = AsyncMock()
        order_dao.get_inflight_orders.return_value = []

        customer_ltv_dao = AsyncMock()
        customer_ltv_dao.get_latest_customer_ltv.return_value = None

        daily_sales_dao = AsyncMock()
        daily_sales_dao.get_daily_revenue.return_value = []

        engineer = LTVFeatureEngineer(
            customer_dao=customer_dao,
            order_dao=order_dao,
            customer_ltv_dao=customer_ltv_dao,
            daily_sales_dao=daily_sales_dao,
        )

        # Should not raise exception
        features = await engineer.compute_features(customer_id)
        assert features is not None

    @pytest.mark.asyncio
    async def test_compute_features_for_new_customer(self):
        """Test feature computation for new customer."""
        from src.features.ltv_features import LTVFeatureEngineer

        customer_id = uuid4()

        # New customer with no order history
        customer_dao = AsyncMock()
        customer_dao.get_customer.return_value = {
            "customer_id": str(customer_id),
            "current_ltv": 0.0,
            "total_orders": 0,
            "loyalty_tier": "BRONZE",
            "created_at": datetime.utcnow(),
        }

        order_dao = AsyncMock()
        order_dao.get_inflight_orders.return_value = []

        customer_ltv_dao = AsyncMock()
        customer_ltv_dao.get_latest_customer_ltv.return_value = None

        daily_sales_dao = AsyncMock()
        daily_sales_dao.get_daily_revenue.return_value = []

        engineer = LTVFeatureEngineer(
            customer_dao=customer_dao,
            order_dao=order_dao,
            customer_ltv_dao=customer_ltv_dao,
            daily_sales_dao=daily_sales_dao,
        )

        features = await engineer.compute_features(customer_id)
        assert features is not None
        # New customer should have zero/low initial values
        assert features.cumulative_orders == 0
        assert features.historical_ltv == 0.0


class TestLTVFeatureValidation:
    """Test feature validation and data quality checks."""

    def test_feature_value_ranges(self):
        """Test that computed features are within expected ranges."""
        from src.features.ltv_features import LTVFeatureEngineer

        engineer = LTVFeatureEngineer(
            customer_dao=MagicMock(),
            order_dao=MagicMock(),
            customer_ltv_dao=MagicMock(),
            daily_sales_dao=MagicMock(),
        )

        # LTV should be non-negative
        ltv = engineer._compute_historical_ltv({"current_ltv": 500.0})
        assert ltv >= 0

        # Repeat purchase rate should be 0-1
        rate = engineer._compute_repeat_purchase_rate(10, 5)
        assert 0 <= rate <= 1


class TestLTVFeatureIntegration:
    """Integration tests for LTV feature engineering."""

    @pytest.mark.asyncio
    async def test_ltv_feature_engineer_full_pipeline(self):
        """Test complete pipeline: customer → DAOs → features."""
        from src.features.ltv_features import LTVFeatureEngineer

        customer_id = uuid4()
        now = datetime.utcnow()

        # Setup realistic mock data
        customer_dao = AsyncMock()
        customer_dao.get_customer.return_value = {
            "customer_id": str(customer_id),
            "current_ltv": 3200.50,
            "total_orders": 48,
            "loyalty_tier": "GOLD",
            "acquired_at": now - timedelta(days=365),
        }

        order_dao = AsyncMock()
        order_dao.get_inflight_orders.return_value = []

        customer_ltv_dao = AsyncMock()
        customer_ltv_dao.get_latest_customer_ltv.return_value = {
            "ltv": 3100.0,
            "cumulative_orders": 45,
        }

        daily_sales_dao = AsyncMock()
        daily_sales_dao.get_daily_revenue.return_value = [
            {"summary_date": now - timedelta(days=30), "net_revenue": 150000},
            {"summary_date": now - timedelta(days=60), "net_revenue": 160000},
        ]

        engineer = LTVFeatureEngineer(
            customer_dao=customer_dao,
            order_dao=order_dao,
            customer_ltv_dao=customer_ltv_dao,
            daily_sales_dao=daily_sales_dao,
        )

        features = await engineer.compute_features(customer_id)

        assert features is not None
        assert str(features.customer_id) == str(customer_id)
        assert features.cumulative_orders == 48  # Current customer total_orders
        assert features.loyalty_tier > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
