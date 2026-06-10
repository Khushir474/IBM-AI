"""Tests for Task 1.6: Dynamic Pricing Feature Engineering."""

import pytest
from uuid import uuid4
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock


class TestPricingFeatureEngineerImports:
    """Verify pricing feature engineer module can be imported."""

    def test_pricing_feature_engineer_importable(self):
        """Test that PricingFeatureEngineer can be imported."""
        try:
            from src.features.pricing_features import PricingFeatureEngineer
            assert PricingFeatureEngineer is not None
        except ImportError as e:
            pytest.fail(f"Failed to import PricingFeatureEngineer: {e}")

    def test_pricing_features_schema_importable(self):
        """Test that PricingFeatures schema can be imported."""
        try:
            from src.features.pricing_features import PricingFeatures
            assert PricingFeatures is not None
        except ImportError as e:
            pytest.fail(f"Failed to import PricingFeatures schema: {e}")


class TestPricingFeatureEngineerInitialization:
    """Test PricingFeatureEngineer initialization."""

    def test_pricing_feature_engineer_initialization(self):
        """Test PricingFeatureEngineer can be initialized."""
        from src.features.pricing_features import PricingFeatureEngineer

        engineer = PricingFeatureEngineer(
            product_dao=MagicMock(),
            daily_sales_dao=MagicMock(),
            product_perf_dao=MagicMock(),
            competitor_dao=MagicMock(),
        )

        assert engineer is not None


class TestPricingFeatureComputation:
    """Test individual pricing feature computations."""

    def test_inventory_days_supply_computation(self):
        """Test computing inventory_days_supply feature."""
        from src.features.pricing_features import PricingFeatureEngineer

        engineer = PricingFeatureEngineer(
            product_dao=MagicMock(),
            daily_sales_dao=MagicMock(),
            product_perf_dao=MagicMock(),
            competitor_dao=MagicMock(),
        )

        # 1000 units in stock, 100 units/day = 10 days supply
        days = engineer._compute_inventory_days_supply(1000, 100)
        assert days == 10.0

    def test_price_elasticity_computation(self):
        """Test computing price_elasticity feature."""
        from src.features.pricing_features import PricingFeatureEngineer

        engineer = PricingFeatureEngineer(
            product_dao=MagicMock(),
            daily_sales_dao=MagicMock(),
            product_perf_dao=MagicMock(),
            competitor_dao=MagicMock(),
        )

        # Default elasticity if unknown
        elasticity = engineer._compute_price_elasticity(None)
        assert elasticity == -1.2  # Default elasticity

    def test_competitor_price_gap_computation(self):
        """Test computing competitor_price_gap feature."""
        from src.features.pricing_features import PricingFeatureEngineer

        engineer = PricingFeatureEngineer(
            product_dao=MagicMock(),
            daily_sales_dao=MagicMock(),
            product_perf_dao=MagicMock(),
            competitor_dao=MagicMock(),
        )

        # Our price $100, competitor $95 = +$5 gap
        gap = engineer._compute_competitor_price_gap(100.0, 95.0)
        assert gap == 5.0

    def test_product_margin_pct_computation(self):
        """Test computing product_margin_pct feature."""
        from src.features.pricing_features import PricingFeatureEngineer

        engineer = PricingFeatureEngineer(
            product_dao=MagicMock(),
            daily_sales_dao=MagicMock(),
            product_perf_dao=MagicMock(),
            competitor_dao=MagicMock(),
        )

        # Price $100, cost $60 = 40% margin
        margin = engineer._compute_product_margin_pct(100.0, 60.0)
        assert margin == 0.4


class TestPricingFeatureVectorGeneration:
    """Test complete pricing feature vector generation."""

    @pytest.mark.asyncio
    async def test_compute_features_complete_vector(self):
        """Test computing complete feature vector for pricing."""
        from src.features.pricing_features import PricingFeatureEngineer

        product_id = uuid4()

        # Mock DAOs
        product_dao = AsyncMock()
        product_dao.get_product.return_value = {
            "product_id": str(product_id),
            "price": 99.99,
            "cost": 49.99,
            "stock_quantity": 5000,
        }

        daily_sales_dao = AsyncMock()
        daily_sales_dao.get_daily_revenue.return_value = [
            {"summary_date": date.today() - timedelta(days=i), "units_sold": 200}
            for i in range(30)
        ]

        product_perf_dao = AsyncMock()
        product_perf_dao.get_weekly_performance.return_value = [
            {"units_sold": 500, "return_rate": 0.05},
        ]

        competitor_dao = AsyncMock()
        competitor_dao.get_latest_competitor_prices.return_value = [
            {"competitor_price": 95.0},
        ]

        engineer = PricingFeatureEngineer(
            product_dao=product_dao,
            daily_sales_dao=daily_sales_dao,
            product_perf_dao=product_perf_dao,
            competitor_dao=competitor_dao,
        )

        features = await engineer.compute_features(product_id)

        # Verify all 6 features are present
        assert features is not None
        assert hasattr(features, "inventory_days_supply")
        assert hasattr(features, "price_elasticity")
        assert hasattr(features, "competitor_price_gap")
        assert hasattr(features, "product_margin_pct")
        assert hasattr(features, "weekly_units_sold")
        assert hasattr(features, "weekly_return_rate")

    @pytest.mark.asyncio
    async def test_compute_features_with_missing_data(self):
        """Test feature computation handles missing data gracefully."""
        from src.features.pricing_features import PricingFeatureEngineer

        product_id = uuid4()

        # Mock DAOs with minimal data
        product_dao = AsyncMock()
        product_dao.get_product.return_value = {
            "product_id": str(product_id),
            "price": 50.0,
            "cost": 25.0,
            "stock_quantity": 0,
        }

        daily_sales_dao = AsyncMock()
        daily_sales_dao.get_daily_revenue.return_value = []

        product_perf_dao = AsyncMock()
        product_perf_dao.get_weekly_performance.return_value = []

        competitor_dao = AsyncMock()
        competitor_dao.get_latest_competitor_prices.return_value = []

        engineer = PricingFeatureEngineer(
            product_dao=product_dao,
            daily_sales_dao=daily_sales_dao,
            product_perf_dao=product_perf_dao,
            competitor_dao=competitor_dao,
        )

        # Should not raise exception
        features = await engineer.compute_features(product_id)
        assert features is not None

    @pytest.mark.asyncio
    async def test_compute_features_for_new_product(self):
        """Test feature computation for new product (no history)."""
        from src.features.pricing_features import PricingFeatureEngineer

        product_id = uuid4()

        # New product with minimal data
        product_dao = AsyncMock()
        product_dao.get_product.return_value = {
            "product_id": str(product_id),
            "price": 79.99,
            "cost": 39.99,
            "stock_quantity": 1000,
            "created_at": datetime.utcnow(),
        }

        daily_sales_dao = AsyncMock()
        daily_sales_dao.get_daily_revenue.return_value = []

        product_perf_dao = AsyncMock()
        product_perf_dao.get_weekly_performance.return_value = []

        competitor_dao = AsyncMock()
        competitor_dao.get_latest_competitor_prices.return_value = []

        engineer = PricingFeatureEngineer(
            product_dao=product_dao,
            daily_sales_dao=daily_sales_dao,
            product_perf_dao=product_perf_dao,
            competitor_dao=competitor_dao,
        )

        features = await engineer.compute_features(product_id)
        assert features is not None
        # New product should use defaults
        assert features.weekly_units_sold == 0


class TestPricingFeatureValidation:
    """Test feature validation and data quality checks."""

    def test_feature_value_ranges(self):
        """Test that computed features are within expected ranges."""
        from src.features.pricing_features import PricingFeatureEngineer

        engineer = PricingFeatureEngineer(
            product_dao=MagicMock(),
            daily_sales_dao=MagicMock(),
            product_perf_dao=MagicMock(),
            competitor_dao=MagicMock(),
        )

        # Margin should be 0-1
        margin = engineer._compute_product_margin_pct(100.0, 50.0)
        assert 0 <= margin <= 1

        # Days supply should be non-negative
        days = engineer._compute_inventory_days_supply(1000, 100)
        assert days >= 0

    def test_feature_null_handling(self):
        """Test that features handle null/missing values."""
        from src.features.pricing_features import PricingFeatureEngineer

        engineer = PricingFeatureEngineer(
            product_dao=MagicMock(),
            daily_sales_dao=MagicMock(),
            product_perf_dao=MagicMock(),
            competitor_dao=MagicMock(),
        )

        # Zero sales/day should not crash
        days = engineer._compute_inventory_days_supply(100, 0)
        assert days == 0.0  # No sales = 0 days supply

        # Missing elasticity should use default
        elasticity = engineer._compute_price_elasticity(None)
        assert elasticity < 0  # Negative elasticity expected


class TestPricingFeatureIntegration:
    """Integration tests for pricing feature engineering."""

    @pytest.mark.asyncio
    async def test_pricing_feature_engineer_full_pipeline(self):
        """Test complete pipeline: product → DAOs → features."""
        from src.features.pricing_features import PricingFeatureEngineer

        product_id = uuid4()

        # Setup realistic mock data
        product_dao = AsyncMock()
        product_dao.get_product.return_value = {
            "product_id": str(product_id),
            "price": 149.99,
            "cost": 74.99,
            "stock_quantity": 2000,
        }

        daily_sales_dao = AsyncMock()
        daily_sales_dao.get_daily_revenue.return_value = [
            {"summary_date": date.today() - timedelta(days=i), "units_sold": 300}
            for i in range(30)
        ]

        product_perf_dao = AsyncMock()
        product_perf_dao.get_weekly_performance.return_value = [
            {"units_sold": 800, "return_rate": 0.03},
            {"units_sold": 750, "return_rate": 0.04},
        ]

        competitor_dao = AsyncMock()
        competitor_dao.get_latest_competitor_prices.return_value = [
            {"competitor_price": 139.99},
        ]

        engineer = PricingFeatureEngineer(
            product_dao=product_dao,
            daily_sales_dao=daily_sales_dao,
            product_perf_dao=product_perf_dao,
            competitor_dao=competitor_dao,
        )

        features = await engineer.compute_features(product_id)

        assert features is not None
        assert str(features.product_id) == str(product_id)
        assert features.inventory_days_supply > 0
        assert features.product_margin_pct > 0
        assert features.weekly_units_sold > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
