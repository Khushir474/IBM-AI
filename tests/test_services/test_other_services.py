"""Tests for LTVService, CartService, PricingService (Tasks 3.2-3.4)."""

import pytest
from unittest.mock import Mock

from src.services.ltv_service import LTVService, LTVPredictions
from src.services.cart_service import CartService, AbandonedCart, RecoveryTier
from src.services.pricing_service import PricingService, PriceRecommendation
from src.models.inference import LTVFeatures, CartFeatures, PricingFeatures


class TestLTVService:
    """Test LTVService."""

    def test_ltv_service_initialization(self):
        """Test LTVService initialization."""
        service = LTVService(Mock(), Mock(), Mock())
        assert service.feature_engineer is not None
        assert service.model_inference is not None
        assert service.explainer is not None

    def test_predict_ltv(self):
        """Test LTV prediction."""
        features = LTVFeatures(
            historical_ltv=500.0,
            cohort_avg_ltv=450.0,
            cumulative_orders=15.0,
            product_category_spend=[100.0, 200.0, 200.0],
            repeat_purchase_rate=0.8,
            seasonality_index=1.2,
            loyalty_tier=2.0,
        )

        feature_eng = Mock()
        feature_eng.compute_features.return_value = features

        model_inf = Mock()
        model_inf.predict_ltv_horizons.return_value = {
            "ltv_7day": 50.0,
            "ltv_30day": 150.0,
            "ltv_90day": 450.0,
            "ltv_365day": 600.0,
        }

        explainer = Mock()
        explainer.explain_ltv_prediction.return_value = []

        service = LTVService(feature_eng, model_inf, explainer)
        predictions = service.predict_ltv("cust_123")

        assert predictions is not None
        assert predictions.ltv_90day == 450.0
        assert predictions.ltv_365day == 600.0

    def test_predict_ltv_missing_features(self):
        """Test LTV prediction with missing features."""
        feature_eng = Mock()
        feature_eng.compute_features.return_value = None

        service = LTVService(feature_eng, Mock(), Mock())
        predictions = service.predict_ltv("cust_456")

        assert predictions is None

    def test_list_high_value_cohorts(self):
        """Test listing high-value cohorts."""
        service = LTVService(Mock(), Mock(), Mock())
        cohorts = service.list_high_value_cohorts(limit=10)

        assert cohorts == []  # DAO integration not yet implemented

    def test_flag_new_high_potential(self):
        """Test flagging new high-potential customers."""
        service = LTVService(Mock(), Mock(), Mock())
        customers = service.flag_new_high_potential(acquisition_hours=168)

        assert customers == []  # DAO integration not yet implemented


class TestCartService:
    """Test CartService."""

    def test_cart_service_initialization(self):
        """Test CartService initialization."""
        service = CartService(Mock(), Mock(), Mock())
        assert service.feature_engineer is not None
        assert service.model_inference is not None
        assert service.explainer is not None

    def test_score_recovery(self):
        """Test cart recovery scoring."""
        features = CartFeatures(
            cart_value=250.0,
            cart_item_count=3.0,
            item_avg_recovery_rate=0.35,
            customer_repeat_buyer=1.0,
            time_since_abandon=2.5,
            previous_abandon_count=1.0,
            shipping_cost_ratio=0.15,
            device_type=1.0,
        )

        feature_eng = Mock()
        feature_eng.compute_features.return_value = features

        model_inf = Mock()
        model_inf.predict_recovery_probability.return_value = 65.0

        service = CartService(feature_eng, model_inf, Mock())
        score = service.score_recovery("cust_123", "prod_456")

        assert score == 65.0

    def test_recovery_tier_boundaries(self):
        """Test recovery tier boundaries."""
        service = CartService(Mock(), Mock(), Mock())

        assert service._score_to_tier(20) == RecoveryTier.LOW
        assert service._score_to_tier(45) == RecoveryTier.MEDIUM
        assert service._score_to_tier(75) == RecoveryTier.HIGH

    def test_recommend_recovery_offer_default(self):
        """Test default recovery offer recommendation."""
        feature_eng = Mock()
        feature_eng.compute_features.return_value = None

        service = CartService(feature_eng, Mock(), Mock())
        offer = service.recommend_recovery_offer("cust_123", "prod_456")

        assert offer is not None
        assert offer.discount_pct == 10.0

    def test_recommend_recovery_offer_high_shipping(self):
        """Test recovery offer when shipping cost is high."""
        features = CartFeatures(
            cart_value=100.0,
            cart_item_count=2.0,
            item_avg_recovery_rate=0.3,
            customer_repeat_buyer=1.0,
            time_since_abandon=1.0,
            previous_abandon_count=0.0,
            shipping_cost_ratio=0.25,  # High shipping
            device_type=1.0,
        )

        feature_eng = Mock()
        feature_eng.compute_features.return_value = features

        service = CartService(feature_eng, Mock(), Mock())
        offer = service.recommend_recovery_offer("cust_123", "prod_456")

        assert offer.offer_type == "free_shipping"
        assert offer.free_shipping is True

    def test_flag_repeat_abandoners(self):
        """Test flagging repeat abandoners."""
        service = CartService(Mock(), Mock(), Mock())
        customers = service.flag_repeat_abandoners(threshold=3)

        assert customers == []  # DAO integration not yet implemented


class TestPricingService:
    """Test PricingService."""

    def test_pricing_service_initialization(self):
        """Test PricingService initialization."""
        service = PricingService(Mock(), Mock(), Mock())
        assert service.feature_engineer is not None
        assert service.model_inference is not None
        assert service.explainer is not None

    def test_recommend_price(self):
        """Test price recommendation."""
        features = PricingFeatures(
            inventory_days_supply=45.0,
            price_elasticity=0.8,
            competitor_price_gap=5.0,
            product_margin_pct=0.35,
            weekly_units_sold=150.0,
            weekly_return_rate=0.03,
        )

        feature_eng = Mock()
        feature_eng.compute_features.return_value = features

        model_inf = Mock()
        model_inf.recommend_price.return_value = {
            "recommended_price": 89.99,
            "discount_pct": 10.0,
        }

        explainer = Mock()
        explainer.explain_price_recommendation.return_value = []

        service = PricingService(feature_eng, model_inf, explainer)
        recommendation = service.recommend_price("prod_123")

        assert recommendation is not None
        assert recommendation.product_id == "prod_123"

    def test_quantify_impact(self):
        """Test impact quantification."""
        recommendation = PriceRecommendation(
            product_id="prod_123",
            current_price=100.0,
            recommended_price=90.0,
            discount_pct=10.0,
        )

        service = PricingService(Mock(), Mock(), Mock())
        impact = service.quantify_impact("prod_123", recommendation)

        assert "revenue_change_daily" in impact
        assert "units_change_daily" in impact
        assert "margin_pct" in impact

    def test_apply_guardrails_max_discount(self):
        """Test guardrails enforcement on max discount."""
        recommendation = PriceRecommendation(
            product_id="prod_123",
            current_price=100.0,
            recommended_price=70.0,
            discount_pct=30.0,
        )

        service = PricingService(Mock(), Mock(), Mock())
        guardrails = {"max_discount": 20}
        guardrailed = service.apply_guardrails("prod_123", recommendation, guardrails)

        assert guardrailed.discount_pct == 20.0

    def test_handle_inventory_pricing_overstock(self):
        """Test pricing adjustment for overstock."""
        service = PricingService(Mock(), Mock(), Mock())
        strategy = service.handle_inventory_pricing("prod_123", 1000, 90.0)

        assert strategy["strategy"] == "overstock_clearance"
        assert strategy["discount_pct"] == 20

    def test_handle_inventory_pricing_understock(self):
        """Test pricing adjustment for understock."""
        service = PricingService(Mock(), Mock(), Mock())
        strategy = service.handle_inventory_pricing("prod_123", 10, 3.0)

        assert strategy["strategy"] == "preserve_margin"
        assert strategy["discount_pct"] == 0

    def test_prevent_discount_abuse(self):
        """Test discount abuse prevention."""
        service = PricingService(Mock(), Mock(), Mock())

        recent = [
            {"discount_pct": 10},
            {"discount_pct": 15},
            {"discount_pct": 20},
        ]

        result = service.prevent_discount_abuse("prod_123", "cust_456", recent)

        assert result["approved"] is True
        assert result["warning"] is not None
