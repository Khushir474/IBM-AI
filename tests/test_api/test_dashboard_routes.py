"""Tests for dashboard, analytics, and system API routes."""

from unittest.mock import Mock
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.dependencies import (
    get_dashboard_service,
    get_export_service,
    get_churn_service,
    get_cart_service,
)
from src.services.dashboard_service import (
    DashboardKPIs,
    UnifiedCustomerIntelligence,
    ModelPerformanceDashboard,
    DataFreshness,
)


class TestDashboardSummaryEndpoint:
    """Test GET /api/v1/dashboard/summary"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        app.dependency_overrides[get_dashboard_service] = lambda: self.mock_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_dashboard_endpoint_summary_200(self):
        """Test dashboard KPI summary."""
        kpis = DashboardKPIs(
            churn_rate=0.09,
            churn_rate_change=-0.01,
            avg_ltv=520.0,
            ltv_change_pct=0.03,
            cart_recovery_rate=0.18,
            cart_recovery_revenue=250000.0,
            pricing_lift_pct=0.03,
            total_interventions_cost=80000.0,
            total_incremental_revenue=370000.0,
            roi_multiplier=4.6,
            last_updated_iso="2024-06-10T00:00:00Z",
        )
        self.mock_service.get_kpi_summary.return_value = kpis

        response = self.client.get("/api/v1/dashboard/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["churn_rate"] == 0.09
        assert data["roi_multiplier"] == 4.6


class TestCustomerIntelligenceEndpoint:
    """Test GET /api/v1/dashboard/customer/{customer_id}"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        app.dependency_overrides[get_dashboard_service] = lambda: self.mock_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_dashboard_endpoint_customer_200(self):
        """Test customer intelligence retrieval."""
        intelligence = UnifiedCustomerIntelligence(
            customer_id="cust_123",
            churn_risk_score=75.0,
            churn_tier="HIGH",
            ltv_90day=500.0,
            ltv_365day=1500.0,
            ltv_tier="HIGH",
            abandoned_carts_count=2,
            total_abandoned_value=200.0,
            intervention_history=[],
            pricing_sensitivity="high",
            recommended_strategy="VIP nurture",
        )
        self.mock_service.get_customer_intelligence.return_value = intelligence

        response = self.client.get("/api/v1/dashboard/customer/cust_123")

        assert response.status_code == 200
        data = response.json()
        assert data["customer_id"] == "cust_123"
        assert data["recommended_strategy"] == "VIP nurture"


class TestModelPerformanceEndpoint:
    """Test GET /api/v1/models/performance"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        app.dependency_overrides[get_dashboard_service] = lambda: self.mock_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_models_endpoint_performance_200(self):
        """Test model performance metrics."""
        perf = ModelPerformanceDashboard(
            churn_model_auc=0.82,
            churn_model_auc_by_segment={"new": 0.78, "repeat": 0.85},
            ltv_model_mae=50.0,
            ltv_model_mae_by_cohort={"q1": 45.0, "q2": 55.0},
            recovery_model_auc=0.78,
            elasticity_accuracy=0.92,
            drift_detected=False,
            drift_alert_msg=None,
            last_evaluated_iso="2024-06-10T00:00:00Z",
        )
        self.mock_service.get_model_performance.return_value = perf

        response = self.client.get("/api/v1/models/performance")

        assert response.status_code == 200
        data = response.json()
        assert data["churn_model_auc"] == 0.82
        assert data["drift_detected"] is False


class TestDataFreshnessEndpoint:
    """Test GET /api/v1/system/data-freshness"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        app.dependency_overrides[get_dashboard_service] = lambda: self.mock_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_system_endpoint_freshness_200(self):
        """Test data freshness check."""
        freshness = DataFreshness(
            cassandra_last_refresh_minutes_ago=2,
            iceberg_last_refresh_hours_ago=2,
            churn_scores_last_computed_hours_ago=3,
            ltv_predictions_last_computed_hours_ago=3,
            pricing_recommendations_last_computed_hours_ago=3,
            cassandra_sla_minutes=5,
            iceberg_sla_hours=24,
            within_sla=True,
        )
        self.mock_service.get_data_freshness.return_value = freshness

        response = self.client.get("/api/v1/system/data-freshness")

        assert response.status_code == 200
        data = response.json()
        assert data["within_sla"] is True


class TestExportChurnEndpoint:
    """Test POST /api/v1/exports/churn-customers"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_churn_service = Mock()
        self.mock_export_service = Mock()
        app.dependency_overrides[get_churn_service] = lambda: self.mock_churn_service
        app.dependency_overrides[get_export_service] = lambda: self.mock_export_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_export_endpoint_churn_csv_200(self):
        """Test churn customer export as CSV."""
        self.mock_churn_service.list_by_tier.return_value = ([], 0)
        self.mock_export_service.export_churn_customers.return_value = (
            "customer_id,score,tier\n"
        )

        response = self.client.post(
            "/api/v1/exports/churn-customers",
            json={"tier": "HIGH", "limit": 100},
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]


class TestExportRecoveryCartsEndpoint:
    """Test POST /api/v1/exports/recovery-carts"""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_cart_service = Mock()
        self.mock_export_service = Mock()
        app.dependency_overrides[get_cart_service] = lambda: self.mock_cart_service
        app.dependency_overrides[get_export_service] = lambda: self.mock_export_service
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test overrides."""
        app.dependency_overrides.clear()

    def test_export_endpoint_recovery_csv_200(self):
        """Test recovery carts export as CSV."""
        self.mock_cart_service.detect_abandoned_carts.return_value = []
        self.mock_export_service.export_recovery_carts.return_value = (
            "customer_id,product_id,cart_value\n"
        )

        response = self.client.post(
            "/api/v1/exports/recovery-carts",
            json={"tier": "HIGH", "limit": 100},
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
