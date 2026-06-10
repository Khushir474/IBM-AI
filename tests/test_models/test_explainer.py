"""Tests for Explainer (Task 2.2)."""

import pytest

from src.models.explainer import (
    Explainer,
    ExplainabilityFactor,
    FactorDirection,
)


class TestExplainabilityFactor:
    """Test ExplainabilityFactor dataclass."""

    def test_factor_creation(self):
        """Test creating ExplainabilityFactor."""
        factor = ExplainabilityFactor(
            feature_name="days_since_last_purchase",
            description="Days since last purchase: 60 days",
            contribution_score=75.5,
            direction=FactorDirection.INCREASES,
            supporting_value=60.0,
            benchmark_value=30.0,
        )
        assert factor.feature_name == "days_since_last_purchase"
        assert factor.contribution_score == 75.5
        assert factor.direction == FactorDirection.INCREASES

    def test_factor_with_defaults(self):
        """Test creating factor with default optional fields."""
        factor = ExplainabilityFactor(
            feature_name="test",
            description="Test factor",
            contribution_score=50.0,
            direction=FactorDirection.NEUTRAL,
        )
        assert factor.supporting_value is None
        assert factor.benchmark_value is None


class TestExplainerChurnFactors:
    """Test explaining churn predictions."""

    def test_explain_churn_score_high_risk(self):
        """Test explaining high-risk churn score."""
        explainer = Explainer()

        features = {
            "days_since_last_purchase": 90.0,
            "purchase_frequency_30d": 0.0,
            "average_order_value": 50.0,
            "cohort_churn_rate": 0.25,
            "session_engagement_30d": 1.0,
            "return_rate": 0.15,
            "loyalty_tier": 1.0,
        }

        factors = explainer.explain_churn_score(
            customer_id="cust_123",
            score=85.0,
            features=features,
            top_n=3,
        )

        assert len(factors) <= 3
        assert all(isinstance(f, ExplainabilityFactor) for f in factors)
        assert all(f.contribution_score >= 0 for f in factors)

    def test_explain_churn_score_low_risk(self):
        """Test explaining low-risk churn score."""
        explainer = Explainer()

        features = {
            "days_since_last_purchase": 5.0,
            "purchase_frequency_30d": 8.0,
            "average_order_value": 300.0,
            "cohort_churn_rate": 0.05,
            "session_engagement_30d": 20.0,
            "return_rate": 0.02,
            "loyalty_tier": 3.0,
        }

        factors = explainer.explain_churn_score(
            customer_id="cust_456",
            score=15.0,
            features=features,
            top_n=3,
        )

        assert len(factors) <= 3
        assert all(0 <= f.contribution_score <= 100 for f in factors)

    def test_churn_explanation_sorted_by_contribution(self):
        """Test factors are sorted by contribution score (descending)."""
        explainer = Explainer()

        features = {
            "days_since_last_purchase": 60.0,
            "purchase_frequency_30d": 2.0,
            "average_order_value": 100.0,
            "cohort_churn_rate": 0.15,
            "session_engagement_30d": 5.0,
            "return_rate": 0.1,
            "loyalty_tier": 2.0,
        }

        factors = explainer.explain_churn_score(
            customer_id="cust_789",
            score=60.0,
            features=features,
        )

        # Check sorted in descending order
        for i in range(len(factors) - 1):
            assert factors[i].contribution_score >= factors[i + 1].contribution_score

    def test_churn_explanation_top_n(self):
        """Test top_n parameter limits number of factors."""
        explainer = Explainer()

        features = {
            "days_since_last_purchase": 30.0,
            "purchase_frequency_30d": 5.0,
            "average_order_value": 150.0,
            "cohort_churn_rate": 0.15,
            "session_engagement_30d": 10.0,
            "return_rate": 0.05,
            "loyalty_tier": 2.0,
        }

        factors_top3 = explainer.explain_churn_score(
            customer_id="cust_123",
            score=50.0,
            features=features,
            top_n=3,
        )
        factors_top5 = explainer.explain_churn_score(
            customer_id="cust_123",
            score=50.0,
            features=features,
            top_n=5,
        )

        assert len(factors_top3) <= 3
        assert len(factors_top5) <= 5

    def test_churn_factor_descriptions_readable(self):
        """Test factor descriptions are human-readable."""
        explainer = Explainer()

        features = {
            "days_since_last_purchase": 45.0,
            "purchase_frequency_30d": 3.0,
            "average_order_value": 200.0,
            "cohort_churn_rate": 0.1,
            "session_engagement_30d": 8.0,
            "return_rate": 0.08,
            "loyalty_tier": 2.0,
        }

        factors = explainer.explain_churn_score(
            customer_id="cust_123",
            score=50.0,
            features=features,
        )

        for factor in factors:
            # Description should contain the feature name or readable version
            assert len(factor.description) > 0
            assert ":" in factor.description  # Should have format "Name: value"


class TestExplainerLTVFactors:
    """Test explaining LTV predictions."""

    def test_explain_ltv_prediction_high_value(self):
        """Test explaining high-value LTV prediction."""
        explainer = Explainer()

        features = {
            "historical_ltv": 1000.0,
            "cohort_avg_ltv": 800.0,
            "cumulative_orders": 25.0,
            "repeat_purchase_rate": 0.9,
            "seasonality_index": 1.3,
            "loyalty_tier": 3.0,
        }
        predictions = {
            "ltv_7day": 100.0,
            "ltv_30day": 350.0,
            "ltv_90day": 900.0,
            "ltv_365day": 1200.0,
        }

        factors = explainer.explain_ltv_prediction(
            customer_id="cust_123",
            predictions=predictions,
            features=features,
            top_n=3,
        )

        assert len(factors) <= 3
        assert all(isinstance(f, ExplainabilityFactor) for f in factors)

    def test_explain_ltv_prediction_low_value(self):
        """Test explaining low-value LTV prediction."""
        explainer = Explainer()

        features = {
            "historical_ltv": 100.0,
            "cohort_avg_ltv": 150.0,
            "cumulative_orders": 2.0,
            "repeat_purchase_rate": 0.2,
            "seasonality_index": 0.8,
            "loyalty_tier": 1.0,
        }
        predictions = {
            "ltv_7day": 10.0,
            "ltv_30day": 30.0,
            "ltv_90day": 80.0,
            "ltv_365day": 120.0,
        }

        factors = explainer.explain_ltv_prediction(
            customer_id="cust_456",
            predictions=predictions,
            features=features,
            top_n=3,
        )

        assert len(factors) <= 3

    def test_ltv_factor_descriptions_include_values(self):
        """Test LTV factor descriptions include actual values."""
        explainer = Explainer()

        features = {
            "historical_ltv": 500.0,
            "cohort_avg_ltv": 450.0,
            "cumulative_orders": 15.0,
            "repeat_purchase_rate": 0.8,
            "seasonality_index": 1.2,
            "loyalty_tier": 2.0,
        }
        predictions = {
            "ltv_7day": 50.0,
            "ltv_30day": 150.0,
            "ltv_90day": 450.0,
            "ltv_365day": 600.0,
        }

        factors = explainer.explain_ltv_prediction(
            customer_id="cust_789",
            predictions=predictions,
            features=features,
        )

        for factor in factors:
            assert len(factor.description) > 0
            assert factor.supporting_value is not None


class TestExplainerCartAbandonmentFactors:
    """Test explaining cart abandonment."""

    def test_explain_cart_abandonment_high_recovery(self):
        """Test explaining high-recovery abandonment."""
        explainer = Explainer()

        features = {
            "cart_value": 100.0,
            "cart_item_count": 2.0,
            "item_avg_recovery_rate": 0.45,
            "customer_repeat_buyer": 1.0,
            "time_since_abandon": 1.0,
            "previous_abandon_count": 0.0,
            "shipping_cost_ratio": 0.08,
        }

        factors = explainer.explain_cart_abandonment(
            customer_id="cust_123",
            product_id="prod_456",
            score=75.0,
            features=features,
            top_n=3,
        )

        assert len(factors) <= 3
        assert all(isinstance(f, ExplainabilityFactor) for f in factors)

    def test_explain_cart_abandonment_low_recovery(self):
        """Test explaining low-recovery abandonment."""
        explainer = Explainer()

        features = {
            "cart_value": 500.0,
            "cart_item_count": 8.0,
            "item_avg_recovery_rate": 0.1,
            "customer_repeat_buyer": 0.0,
            "time_since_abandon": 5.0,
            "previous_abandon_count": 3.0,
            "shipping_cost_ratio": 0.3,
        }

        factors = explainer.explain_cart_abandonment(
            customer_id="cust_789",
            product_id="prod_000",
            score=20.0,
            features=features,
            top_n=3,
        )

        assert len(factors) <= 3

    def test_cart_abandonment_factors_human_readable(self):
        """Test cart abandonment factors are human-readable."""
        explainer = Explainer()

        features = {
            "cart_value": 250.0,
            "cart_item_count": 3.0,
            "item_avg_recovery_rate": 0.35,
            "customer_repeat_buyer": 1.0,
            "time_since_abandon": 2.5,
            "previous_abandon_count": 1.0,
            "shipping_cost_ratio": 0.15,
        }

        factors = explainer.explain_cart_abandonment(
            customer_id="cust_123",
            product_id="prod_456",
            score=50.0,
            features=features,
        )

        for factor in factors:
            assert ":" in factor.description
            assert factor.supporting_value is not None
            # Should include dollar signs for cart_value
            if "value" in factor.feature_name.lower():
                assert "$" in factor.description


class TestExplainerPricingFactors:
    """Test explaining pricing recommendations."""

    def test_explain_price_recommendation(self):
        """Test explaining price recommendation."""
        explainer = Explainer()

        features = {
            "inventory_days_supply": 45.0,
            "price_elasticity": 0.8,
            "competitor_price_gap": 5.0,
            "product_margin_pct": 0.35,
            "weekly_units_sold": 150.0,
            "weekly_return_rate": 0.03,
        }
        recommendation = {
            "recommended_price": 89.99,
            "discount_pct": 10.0,
        }

        factors = explainer.explain_price_recommendation(
            product_id="prod_123",
            recommendation=recommendation,
            features=features,
            top_n=3,
        )

        assert len(factors) <= 3
        assert all(isinstance(f, ExplainabilityFactor) for f in factors)

    def test_pricing_factors_human_readable(self):
        """Test pricing factors are human-readable."""
        explainer = Explainer()

        features = {
            "inventory_days_supply": 60.0,
            "price_elasticity": 1.2,
            "competitor_price_gap": -3.0,
            "product_margin_pct": 0.4,
            "weekly_units_sold": 200.0,
            "weekly_return_rate": 0.02,
        }
        recommendation = {
            "recommended_price": 99.99,
            "discount_pct": 15.0,
        }

        factors = explainer.explain_price_recommendation(
            product_id="prod_999",
            recommendation=recommendation,
            features=features,
        )

        for factor in factors:
            assert len(factor.description) > 0


class TestExplainerFactorDirection:
    """Test FactorDirection enum."""

    def test_factor_direction_values(self):
        """Test FactorDirection has correct values."""
        assert FactorDirection.INCREASES == "increases"
        assert FactorDirection.DECREASES == "decreases"
        assert FactorDirection.NEUTRAL == "neutral"

    def test_factor_with_direction(self):
        """Test creating factors with different directions."""
        for direction in [
            FactorDirection.INCREASES,
            FactorDirection.DECREASES,
            FactorDirection.NEUTRAL,
        ]:
            factor = ExplainabilityFactor(
                feature_name="test",
                description="Test",
                contribution_score=50.0,
                direction=direction,
            )
            assert factor.direction == direction


class TestExplainerIntegration:
    """Integration tests for explainer."""

    def test_explain_different_modules(self):
        """Test explaining predictions from all modules."""
        explainer = Explainer()

        # Churn
        churn_features = {
            "days_since_last_purchase": 30.0,
            "purchase_frequency_30d": 5.0,
            "average_order_value": 150.0,
            "cohort_churn_rate": 0.15,
            "session_engagement_30d": 10.0,
            "return_rate": 0.05,
            "loyalty_tier": 2.0,
        }
        churn_factors = explainer.explain_churn_score(
            "cust_1", 50.0, churn_features
        )
        assert len(churn_factors) > 0

        # LTV
        ltv_features = {
            "historical_ltv": 500.0,
            "cohort_avg_ltv": 450.0,
            "cumulative_orders": 15.0,
            "repeat_purchase_rate": 0.8,
            "seasonality_index": 1.2,
            "loyalty_tier": 2.0,
        }
        ltv_preds = {
            "ltv_7day": 50.0,
            "ltv_30day": 150.0,
            "ltv_90day": 450.0,
            "ltv_365day": 600.0,
        }
        ltv_factors = explainer.explain_ltv_prediction(
            "cust_1", ltv_preds, ltv_features
        )
        assert len(ltv_factors) > 0

        # Cart
        cart_features = {
            "cart_value": 250.0,
            "cart_item_count": 3.0,
            "item_avg_recovery_rate": 0.35,
            "customer_repeat_buyer": 1.0,
            "time_since_abandon": 2.5,
            "previous_abandon_count": 1.0,
            "shipping_cost_ratio": 0.15,
        }
        cart_factors = explainer.explain_cart_abandonment(
            "cust_1", "prod_1", 50.0, cart_features
        )
        assert len(cart_factors) > 0

        # Pricing
        pricing_features = {
            "inventory_days_supply": 45.0,
            "price_elasticity": 0.8,
            "competitor_price_gap": 5.0,
            "product_margin_pct": 0.35,
            "weekly_units_sold": 150.0,
            "weekly_return_rate": 0.03,
        }
        pricing_factors = explainer.explain_price_recommendation(
            "prod_1", {"recommended_price": 89.99, "discount_pct": 10.0}, pricing_features
        )
        assert len(pricing_factors) > 0
