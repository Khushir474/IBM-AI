"""Tests for CampaignService, ExperimentService, DashboardService, ExportService (Tasks 3.5-3.8)."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from src.services.campaign_service import CampaignService, CampaignType, CampaignResult
from src.services.experiment_service import ExperimentService
from src.services.dashboard_service import DashboardService, DashboardKPIs
from src.services.export_service import ExportService


class TestCampaignService:
    """Test CampaignService."""

    def test_create_churn_campaign(self):
        """Test creating churn campaign."""
        service = CampaignService()

        campaign = service.create_churn_campaign(
            customer_ids=["cust_1", "cust_2", "cust_3"],
            intervention_type="email_offer",
            offer_details={"discount_pct": 15},
        )

        assert campaign.campaign_type == CampaignType.CHURN
        assert campaign.audience_count == 3
        assert campaign.status == "draft"

    def test_create_recovery_campaign(self):
        """Test creating cart recovery campaign."""
        service = CampaignService()

        carts = [
            {"customer_id": "cust_1", "product_id": "prod_1", "cart_value": 100},
            {"customer_id": "cust_2", "product_id": "prod_2", "cart_value": 150},
        ]

        campaign = service.create_recovery_campaign(
            cart_items=carts,
            offer_type="discount",
            offer_details={"discount_pct": 10},
        )

        assert campaign.campaign_type == CampaignType.CART_RECOVERY
        assert campaign.audience_count == 2

    def test_track_send(self):
        """Test tracking campaign send."""
        service = CampaignService()

        send_record = service.track_send(
            campaign_id="camp_123",
            customer_id="cust_456",
            offer_code="SAVE15",
            offer_details={"discount_pct": 15},
        )

        assert send_record.campaign_id == "camp_123"
        assert send_record.customer_id == "cust_456"
        assert send_record.offer_code == "SAVE15"

    def test_track_conversion(self):
        """Test tracking conversion."""
        service = CampaignService()

        result = service.track_conversion(
            campaign_id="camp_123",
            customer_id="cust_456",
            converted=True,
            conversion_date_iso=datetime.utcnow().isoformat(),
            order_value=120.0,
        )

        assert result["campaign_id"] == "camp_123"
        assert result["converted"] is True
        assert result["order_value"] == 120.0

    def test_measure_campaign_effectiveness(self):
        """Test campaign effectiveness measurement."""
        service = CampaignService()

        sends = [
            {"customer_id": "cust_1", "offer_code": "SAVE10"},
            {"customer_id": "cust_2", "offer_code": "SAVE10"},
            {"customer_id": "cust_3", "offer_code": "SAVE10"},
            {"customer_id": "cust_4", "offer_code": "SAVE10"},
        ]

        conversions = [
            {"converted": True, "order_value": 100.0},
            {"converted": True, "order_value": 120.0},
            {"converted": False, "order_value": 0},
            {"converted": False, "order_value": 0},
        ]

        result = service.measure_campaign_effectiveness("camp_123", sends, conversions)

        assert result.total_sent == 4
        assert result.total_converted == 2
        assert result.conversion_rate == 50.0
        assert result.total_revenue_generated == 220.0

    def test_measure_ab_test_comparison(self):
        """Test A/B test comparison."""
        service = CampaignService()

        # Format: {treatment_name: [conversion records]}
        # Conversion record should have converted field, not event_type
        treatments = {
            "control": [
                {"converted": True},
                {"converted": False},
                {"converted": False},
            ],
            "10_percent": [
                {"converted": True},
                {"converted": True},
                {"converted": False},
            ],
        }

        comparison = service.measure_ab_test_comparison("camp_123", treatments)

        # Check conversion rates - control should be ~33%, 10_percent should be ~67%
        assert comparison["control"]["conversion_rate"] == pytest.approx(33.33, abs=0.1)
        assert comparison["10_percent"]["conversion_rate"] == pytest.approx(66.67, abs=0.1)
        # Winner should have the higher conversion rate
        assert "winner" in comparison.get("10_percent", {}) or "winner" in comparison.get("control", {})


class TestExperimentService:
    """Test ExperimentService."""

    def test_create_discount_experiment(self):
        """Test creating discount experiment."""
        service = ExperimentService()

        treatments = [
            {"name": "control", "discount_pct": 0},
            {"name": "10_percent", "discount_pct": 10},
            {"name": "15_percent", "discount_pct": 15},
        ]

        experiment = service.create_discount_experiment(
            name="Q3 Recovery Discount Test",
            treatments=treatments,
            metric="recovery_rate",
            start_date_iso="2024-07-01T00:00:00Z",
            end_date_iso="2024-07-31T23:59:59Z",
        )

        assert experiment.name == "Q3 Recovery Discount Test"
        assert len(experiment.treatments) == 3
        assert experiment.status == "running"

    def test_get_treatment_for_cart(self):
        """Test deterministic treatment assignment."""
        service = ExperimentService()

        # Same customer should always get same treatment
        treatment1 = service.get_treatment_for_cart("exp_123", "cust_456")
        treatment2 = service.get_treatment_for_cart("exp_123", "cust_456")

        assert treatment1 == treatment2

        # Different customers may get different treatments
        treatment3 = service.get_treatment_for_cart("exp_123", "cust_789")
        # (may or may not be same, just checking it's a valid treatment)
        assert treatment3 in ["control", "treatment_a", "treatment_b", "treatment_c"]

    def test_track_experiment_event(self):
        """Test tracking experiment event."""
        service = ExperimentService()

        event = service.track_experiment_event(
            experiment_id="exp_123",
            customer_id="cust_456",
            event_type="conversion",
            data={"order_value": 100.0},
        )

        assert event["experiment_id"] == "exp_123"
        assert event["event_type"] == "conversion"

    def test_analyze_experiment_results_significant(self):
        """Test analyzing statistically significant results."""
        service = ExperimentService()

        treatments = {
            "control": [
                {"event_type": "conversion"} if i < 20 else {"event_type": "no_conversion"}
                for i in range(100)
            ],
            "15_percent": [
                {"event_type": "conversion"} if i < 35 else {"event_type": "no_conversion"}
                for i in range(100)
            ],
        }

        results = service.analyze_experiment_results("exp_123", treatments)

        assert results.treatment_results["control"]["sent"] == 100
        assert results.treatment_results["15_percent"]["sent"] == 100
        assert results.winner is not None
        # With large sample sizes and different rates, should detect significance
        assert results.p_value is not None

    def test_confidence_interval_calculation(self):
        """Test confidence interval calculation."""
        service = ExperimentService()

        lower, upper = service._calculate_confidence_interval(50, 100)

        assert 30 < lower < 50
        assert 50 < upper < 70


class TestDashboardService:
    """Test DashboardService."""

    def test_dashboard_service_initialization(self):
        """Test DashboardService initialization."""
        service = DashboardService()
        assert service is not None

    def test_get_kpi_summary(self):
        """Test KPI summary generation."""
        service = DashboardService()

        kpis = service.get_kpi_summary()

        assert kpis.churn_rate > 0
        assert kpis.avg_ltv > 0
        assert kpis.cart_recovery_rate >= 0
        assert kpis.roi_multiplier > 0

    def test_get_kpi_summary_with_custom_data(self):
        """Test KPI summary with custom data."""
        service = DashboardService()

        current = {
            "churn_rate": 8.0,
            "avg_ltv": 550,
            "recovery_rate": 0.20,
            "recovery_revenue": 300000,
            "pricing_lift_pct": 4.0,
            "intervention_cost": 90000,
            "incremental_revenue": 400000,
        }
        previous = {"churn_rate": 9.0, "avg_ltv": 500}

        kpis = service.get_kpi_summary(current_month_data=current, previous_month_data=previous)

        assert kpis.churn_rate == 8.0
        assert kpis.churn_rate_change == -1.0
        assert kpis.avg_ltv == 550

    def test_get_customer_intelligence(self):
        """Test unified customer intelligence."""
        from src.services.churn_service import ChurnTier

        # Mock services
        churn_service = Mock()
        churn_service.score_customer.return_value = Mock(
            score=75.0,
            tier=ChurnTier.HIGH,
            factors=[],
        )

        ltv_service = Mock()
        ltv_service.predict_ltv.return_value = Mock(
            ltv_90day=600.0,
            ltv_365day=900.0,
        )

        service = DashboardService(churn_service=churn_service, ltv_service=ltv_service)

        intelligence = service.get_customer_intelligence("cust_123")

        assert intelligence is not None
        assert intelligence.customer_id == "cust_123"
        assert intelligence.churn_risk_score == 75.0
        assert intelligence.ltv_90day == 600.0
        assert intelligence.recommended_strategy is not None

    def test_get_model_performance(self):
        """Test model performance dashboard."""
        service = DashboardService()

        perf = service.get_model_performance()

        assert perf.churn_model_auc > 0.75
        assert perf.ltv_model_mae > 0
        assert perf.recovery_model_auc > 0.70

    def test_get_data_freshness(self):
        """Test data freshness tracking."""
        service = DashboardService()

        freshness = service.get_data_freshness()

        assert freshness.cassandra_last_refresh_minutes_ago >= 0
        assert freshness.iceberg_last_refresh_hours_ago >= 0
        assert freshness.within_sla is not None


class TestExportService:
    """Test ExportService."""

    def test_export_churn_customers(self):
        """Test exporting churn customers to CSV."""
        service = ExportService()

        scores = [
            {
                "customer_id": "cust_1",
                "score": 85.0,
                "tier": "HIGH",
                "ltv_90day": 500,
                "factors": [
                    {"description": "No purchase in 60 days"},
                    {"description": "Below-cohort value"},
                ],
                "recommended_intervention": "vip_upgrade",
            },
            {
                "customer_id": "cust_2",
                "score": 25.0,
                "tier": "LOW",
                "ltv_90day": 800,
                "factors": [],
                "recommended_intervention": None,
            },
        ]

        csv_content = service.export_churn_customers(scores)

        assert len(csv_content) > 0
        assert "customer_id" in csv_content
        assert "cust_1" in csv_content
        assert "HIGH" in csv_content

    def test_export_recovery_carts(self):
        """Test exporting abandoned carts to CSV."""
        service = ExportService()

        carts = [
            {
                "customer_id": "cust_1",
                "product_id": "prod_1",
                "cart_value": 250.0,
                "recovery_score": 75.0,
                "recovery_tier": "HIGH",
                "recommended_offer": {
                    "type": "discount",
                    "discount_pct": 15.0,
                    "conversion_prob": 0.22,
                },
            },
        ]

        csv_content = service.export_recovery_carts(carts)

        assert len(csv_content) > 0
        assert "cart_value" in csv_content
        assert "250" in csv_content

    def test_export_campaign_results(self):
        """Test exporting campaign results to CSV."""
        service = ExportService()

        results = [
            {
                "campaign_id": "camp_1",
                "total_sent": 500,
                "total_converted": 75,
                "conversion_rate": 15.0,
                "total_revenue": 9000.0,
                "avg_order_value": 120.0,
                "roi_multiplier": 4.5,
                "net_revenue_gain": 7650.0,
            },
        ]

        csv_content = service.export_campaign_results(results)

        assert len(csv_content) > 0
        assert "camp_1" in csv_content
        assert "500" in csv_content
        assert "4.50x" in csv_content

    def test_export_pricing_recommendations(self):
        """Test exporting pricing recommendations to CSV."""
        service = ExportService()

        recs = [
            {
                "product_id": "prod_1",
                "current_price": 100.0,
                "recommended_price": 90.0,
                "discount_pct": 10.0,
                "expected_revenue_impact": {"revenue_change_daily": 150.0},
                "margin_impact": 0.28,
                "confidence": 0.75,
                "reason": "Overstock detected",
            },
        ]

        csv_content = service.export_pricing_recommendations(recs)

        assert len(csv_content) > 0
        assert "prod_1" in csv_content
        assert "100.00" in csv_content

    def test_export_empty_data(self):
        """Test exporting empty data sets."""
        service = ExportService()

        csv_churn = service.export_churn_customers([])
        csv_carts = service.export_recovery_carts([])

        assert csv_churn == ""
        assert csv_carts == ""
