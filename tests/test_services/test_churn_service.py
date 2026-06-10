"""Tests for ChurnService (Task 3.1)."""

import pytest
from unittest.mock import Mock, MagicMock

from src.services.churn_service import ChurnService, ChurnRiskScore, ChurnTier, ChurnIntervention
from src.models.inference import ChurnFeatures


class TestChurnRiskScore:
    """Test ChurnRiskScore dataclass."""

    def test_churn_risk_score_creation(self):
        """Test creating ChurnRiskScore."""
        score = ChurnRiskScore(
            customer_id="cust_123",
            score=75.0,
            tier=ChurnTier.HIGH,
            factors=[{"name": "days_since_purchase", "contribution": 80}],
            recommended_intervention="vip_upgrade",
        )
        assert score.customer_id == "cust_123"
        assert score.score == 75.0
        assert score.tier == ChurnTier.HIGH

    def test_churn_tiers(self):
        """Test ChurnTier enum values."""
        assert ChurnTier.LOW == "LOW"
        assert ChurnTier.MEDIUM == "MEDIUM"
        assert ChurnTier.HIGH == "HIGH"


class TestChurnServiceInitialization:
    """Test ChurnService initialization."""

    def test_init(self):
        """Test ChurnService initialization."""
        feature_eng = Mock()
        model_inf = Mock()
        explainer = Mock()

        service = ChurnService(feature_eng, model_inf, explainer)
        assert service.feature_engineer is feature_eng
        assert service.model_inference is model_inf
        assert service.explainer is explainer


class TestChurnServiceScoring:
    """Test churn scoring functionality."""

    def test_score_customer_high_risk(self):
        """Test scoring high-risk customer."""
        # Setup mocks
        features = ChurnFeatures(
            days_since_last_purchase=90.0,
            purchase_frequency_30d=0.0,
            average_order_value=50.0,
            product_category_affinity=[1.0, 0.0, 0.0],
            cohort_churn_rate=0.25,
            session_engagement_30d=1.0,
            return_rate=0.15,
            loyalty_tier=1.0,
        )

        feature_eng = Mock()
        feature_eng.compute_features.return_value = features

        model_inf = Mock()
        model_inf.predict_churn_score.return_value = 85.0

        explainer = Mock()
        explainer.explain_churn_score.return_value = []

        service = ChurnService(feature_eng, model_inf, explainer)

        # Score customer
        score = service.score_customer("cust_123")

        assert score.customer_id == "cust_123"
        assert score.score == 85.0
        assert score.tier == ChurnTier.HIGH

    def test_score_customer_low_risk(self):
        """Test scoring low-risk customer."""
        features = ChurnFeatures(
            days_since_last_purchase=5.0,
            purchase_frequency_30d=8.0,
            average_order_value=300.0,
            product_category_affinity=[1.0, 0.0, 0.0],
            cohort_churn_rate=0.05,
            session_engagement_30d=20.0,
            return_rate=0.02,
            loyalty_tier=3.0,
        )

        feature_eng = Mock()
        feature_eng.compute_features.return_value = features

        model_inf = Mock()
        model_inf.predict_churn_score.return_value = 15.0

        explainer = Mock()
        explainer.explain_churn_score.return_value = []

        service = ChurnService(feature_eng, model_inf, explainer)
        score = service.score_customer("cust_456")

        assert score.score == 15.0
        assert score.tier == ChurnTier.LOW

    def test_score_customer_missing_features(self):
        """Test scoring when features cannot be computed."""
        feature_eng = Mock()
        feature_eng.compute_features.return_value = None

        model_inf = Mock()
        explainer = Mock()

        service = ChurnService(feature_eng, model_inf, explainer)
        score = service.score_customer("cust_789")

        assert score.customer_id == "cust_789"
        assert score.score == 50.0  # Default neutral score
        assert score.tier == ChurnTier.MEDIUM

    def test_score_customer_with_factors(self):
        """Test that factors are included in score."""
        features = ChurnFeatures(
            days_since_last_purchase=60.0,
            purchase_frequency_30d=2.0,
            average_order_value=100.0,
            product_category_affinity=[1.0, 0.0, 0.0],
            cohort_churn_rate=0.15,
            session_engagement_30d=5.0,
            return_rate=0.1,
            loyalty_tier=2.0,
        )

        feature_eng = Mock()
        feature_eng.compute_features.return_value = features

        model_inf = Mock()
        model_inf.predict_churn_score.return_value = 60.0

        from src.models.explainer import ExplainabilityFactor, FactorDirection

        factor1 = ExplainabilityFactor(
            feature_name="days_since_last_purchase",
            description="Days since last purchase: 60 days",
            contribution_score=50.0,
            direction=FactorDirection.INCREASES,
        )

        explainer = Mock()
        explainer.explain_churn_score.return_value = [factor1]

        service = ChurnService(feature_eng, model_inf, explainer)
        score = service.score_customer("cust_123")

        assert len(score.factors) == 1
        assert score.factors[0]["name"] == "days_since_last_purchase"


class TestChurnServiceBatchScoring:
    """Test batch churn scoring."""

    def test_batch_scoring(self):
        """Test batch scoring multiple customers."""
        feature_eng = Mock()
        feature_eng.compute_features.side_effect = [
            ChurnFeatures(
                days_since_last_purchase=30.0,
                purchase_frequency_30d=5.0,
                average_order_value=150.0,
                product_category_affinity=[1.0, 0.0, 0.0],
                cohort_churn_rate=0.15,
                session_engagement_30d=10.0,
                return_rate=0.05,
                loyalty_tier=2.0,
            ),
            None,
        ]

        model_inf = Mock()
        model_inf.predict_churn_score.side_effect = [50.0]

        explainer = Mock()
        explainer.explain_churn_score.return_value = []

        service = ChurnService(feature_eng, model_inf, explainer)
        scores = service.score_customers_batch(["cust_1", "cust_2"])

        assert len(scores) == 2
        assert scores[0].score == 50.0
        assert scores[1].score == 50.0  # Default for missing features

    def test_batch_scoring_empty(self):
        """Test batch scoring with empty list."""
        service = ChurnService(Mock(), Mock(), Mock())
        scores = service.score_customers_batch([])

        assert scores == []


class TestChurnServiceTierSegmentation:
    """Test tier segmentation."""

    def test_score_to_tier_boundaries(self):
        """Test score to tier conversion at boundaries."""
        service = ChurnService(Mock(), Mock(), Mock())

        assert service._score_to_tier(0) == ChurnTier.LOW
        assert service._score_to_tier(33) == ChurnTier.LOW
        assert service._score_to_tier(34) == ChurnTier.MEDIUM
        assert service._score_to_tier(66) == ChurnTier.MEDIUM
        assert service._score_to_tier(67) == ChurnTier.HIGH
        assert service._score_to_tier(100) == ChurnTier.HIGH

    def test_tier_summary(self):
        """Test getting tier summary counts."""
        service = ChurnService(Mock(), Mock(), Mock())

        pre_computed = {
            "cust_1": 25.0,  # LOW
            "cust_2": 50.0,  # MEDIUM
            "cust_3": 75.0,  # HIGH
            "cust_4": 10.0,  # LOW
            "cust_5": 80.0,  # HIGH
        }

        summary = service.get_tier_summary(pre_computed)

        assert summary[ChurnTier.LOW] == 2
        assert summary[ChurnTier.MEDIUM] == 1
        assert summary[ChurnTier.HIGH] == 2


class TestChurnServiceIntervention:
    """Test intervention recommendation."""

    def test_low_risk_no_intervention(self):
        """Test that low-risk customers get no intervention."""
        service = ChurnService(Mock(), Mock(), Mock())

        intervention = service._compute_intervention(
            score=25.0,
            tier=ChurnTier.LOW,
            features={},
        )

        assert intervention is None

    def test_high_risk_high_value_vip_upgrade(self):
        """Test high-risk, high-value customer gets VIP upgrade."""
        service = ChurnService(Mock(), Mock(), Mock())

        features = {"historical_ltv": 600.0, "days_since_last_purchase": 30.0}

        intervention = service._compute_intervention(
            score=75.0,
            tier=ChurnTier.HIGH,
            features=features,
        )

        assert intervention is not None
        assert intervention.intervention_type == "vip_upgrade"

    def test_high_risk_low_value_email_offer(self):
        """Test high-risk, low-value customer gets email offer."""
        service = ChurnService(Mock(), Mock(), Mock())

        features = {"historical_ltv": 100.0, "days_since_last_purchase": 30.0}

        intervention = service._compute_intervention(
            score=75.0,
            tier=ChurnTier.HIGH,
            features=features,
        )

        assert intervention is not None
        assert intervention.intervention_type == "email_offer"
        assert intervention.recommended_discount is not None

    def test_medium_risk_product_recommendation(self):
        """Test medium-risk customer with old purchase gets product recommendation."""
        service = ChurnService(Mock(), Mock(), Mock())

        features = {"historical_ltv": 300.0, "days_since_last_purchase": 70.0}

        intervention = service._compute_intervention(
            score=50.0,
            tier=ChurnTier.MEDIUM,
            features=features,
        )

        assert intervention is not None
        assert intervention.intervention_type == "product_recommendation"


class TestChurnServiceListByTier:
    """Test listing customers by tier."""

    def test_list_by_tier_high(self):
        """Test listing high-risk customers."""
        feature_eng = Mock()
        feature_eng.compute_features.return_value = ChurnFeatures(
            days_since_last_purchase=60.0,
            purchase_frequency_30d=2.0,
            average_order_value=100.0,
            product_category_affinity=[1.0, 0.0, 0.0],
            cohort_churn_rate=0.15,
            session_engagement_30d=5.0,
            return_rate=0.1,
            loyalty_tier=2.0,
        )

        model_inf = Mock()
        model_inf.predict_churn_score.return_value = 75.0

        explainer = Mock()
        explainer.explain_churn_score.return_value = []

        service = ChurnService(feature_eng, model_inf, explainer)

        pre_computed = {
            "cust_1": 75.0,  # HIGH
            "cust_2": 50.0,  # MEDIUM
            "cust_3": 80.0,  # HIGH
        }

        results, total = service.list_by_tier(ChurnTier.HIGH, limit=10, pre_computed=pre_computed)

        assert total == 2
        assert len(results) <= 2

    def test_list_by_tier_pagination(self):
        """Test pagination in list_by_tier."""
        feature_eng = Mock()
        feature_eng.compute_features.return_value = ChurnFeatures(
            days_since_last_purchase=30.0,
            purchase_frequency_30d=5.0,
            average_order_value=150.0,
            product_category_affinity=[1.0, 0.0, 0.0],
            cohort_churn_rate=0.15,
            session_engagement_30d=10.0,
            return_rate=0.05,
            loyalty_tier=2.0,
        )

        model_inf = Mock()
        model_inf.predict_churn_score.return_value = 50.0

        explainer = Mock()
        explainer.explain_churn_score.return_value = []

        service = ChurnService(feature_eng, model_inf, explainer)

        pre_computed = {f"cust_{i}": 75.0 for i in range(10)}

        results1, total1 = service.list_by_tier(ChurnTier.HIGH, limit=5, offset=0, pre_computed=pre_computed)
        results2, total2 = service.list_by_tier(ChurnTier.HIGH, limit=5, offset=5, pre_computed=pre_computed)

        assert total1 == 10
        assert len(results1) == 5
        assert len(results2) == 5
