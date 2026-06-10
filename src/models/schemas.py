"""Pydantic models for API request/response schemas."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Churn Models
# ============================================================================

class ChurnFactorResponse(BaseModel):
    """Single churn risk factor."""
    factor: str
    contribution_score: float
    description: str


class ChurnInterventionResponse(BaseModel):
    """Recommended intervention for at-risk customer."""
    intervention_type: str
    description: str
    recommended_discount: Optional[float] = None
    confidence: float


class ChurnRiskScoreResponse(BaseModel):
    """Churn risk assessment for a customer."""
    customer_id: str
    score: float
    tier: str
    factors: List[ChurnFactorResponse]
    recommended_intervention: ChurnInterventionResponse
    confidence: float

    model_config = ConfigDict(from_attributes=True)


class PaginatedChurnResponse(BaseModel):
    """Paginated list of churn scores."""
    items: List[ChurnRiskScoreResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# LTV Models
# ============================================================================

class LTVFactorResponse(BaseModel):
    """Single LTV prediction factor."""
    factor: str
    contribution_score: float
    description: str


class LTVPredictionsResponse(BaseModel):
    """LTV predictions at multiple horizons."""
    customer_id: str
    ltv_7day: float
    ltv_30day: float
    ltv_90day: float
    ltv_365day: float
    factors: List[LTVFactorResponse]

    model_config = ConfigDict(from_attributes=True)


class LTVCohortResponse(BaseModel):
    """High-value customer cohort."""
    cohort_name: str
    size: int
    avg_ltv: float
    avg_ltv_7day: float
    avg_ltv_30day: float
    avg_ltv_90day: float
    avg_ltv_365day: float
    characteristics: Dict[str, str]

    model_config = ConfigDict(from_attributes=True)


class HighPotentialCustomerResponse(BaseModel):
    """New customer with high LTV potential."""
    customer_id: str
    days_as_customer: int
    predicted_ltv_90day: float
    confidence: float
    signals: List[str]

    model_config = ConfigDict(from_attributes=True)


class ModelAccuracyMetricsResponse(BaseModel):
    """LTV model accuracy metrics."""
    mean_absolute_error: float
    root_mean_squared_error: float
    mean_absolute_percentage_error: float
    calibration_score: float
    accuracy_by_cohort: Dict[str, float]

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Cart Abandonment Models
# ============================================================================

class AbandonmentFactorResponse(BaseModel):
    """Single cart abandonment factor."""
    factor: str
    contribution_score: float
    description: str


class AbandonedCartResponse(BaseModel):
    """Abandoned cart with recovery info."""
    customer_id: str
    product_id: str
    cart_value: float
    item_count: int
    abandon_time_iso: str
    recovery_score: float
    recovery_tier: str
    factors: List[AbandonmentFactorResponse]
    recommended_offer: Optional[Dict] = None

    model_config = ConfigDict(from_attributes=True)


class RecoveryOfferResponse(BaseModel):
    """Recommended recovery offer for abandoned cart."""
    offer_type: str
    discount_pct: Optional[float] = None
    free_shipping: bool
    conversion_probability: float

    model_config = ConfigDict(from_attributes=True)


class RepeatAbandonerResponse(BaseModel):
    """Customer with repeated abandonment pattern."""
    customer_id: str
    abandon_count_30d: int
    total_abandoned_value_30d: float
    avg_recovery_rate: float
    risk_level: str

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Pricing Models
# ============================================================================

class PriceRecommendationResponse(BaseModel):
    """Price or discount recommendation."""
    product_id: str
    current_price: float
    recommended_price: float
    discount_pct: float
    expected_revenue_impact: float
    margin_impact: float
    confidence: float
    reason: str

    model_config = ConfigDict(from_attributes=True)


class ElasticityEstimateResponse(BaseModel):
    """Price elasticity estimate."""
    product_id: str
    discount_pct: float
    expected_recovery_rate: float
    confidence: float
    sample_size: int
    last_updated_iso: str

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Experiment Models
# ============================================================================

class ExperimentResponse(BaseModel):
    """A/B test experiment."""
    experiment_id: str
    name: str
    treatments: List[Dict]
    metric: str
    start_date_iso: str
    end_date_iso: str
    status: str
    sample_size_per_treatment: int

    model_config = ConfigDict(from_attributes=True)


class TreatmentResultResponse(BaseModel):
    """Results for one experiment treatment."""
    treatment_name: str
    conversion_rate: float
    sample_size: int
    mean_order_value: Optional[float] = None


class ExperimentResultsResponse(BaseModel):
    """Full experiment results with significance."""
    experiment_id: str
    treatment_results: List[TreatmentResultResponse]
    winner: Optional[str] = None
    p_value: Optional[float] = None
    significant_at_95: bool
    recommendation: str

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Campaign Models
# ============================================================================

class CampaignResponse(BaseModel):
    """Campaign created for interventions."""
    campaign_id: str
    campaign_type: str
    created_at_iso: str
    audience_count: int
    offer_details: Dict
    status: str
    scheduled_send_time_iso: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CampaignResultsResponse(BaseModel):
    """Campaign effectiveness and ROI."""
    campaign_id: str
    total_sent: int
    total_converted: int
    conversion_rate: float
    total_revenue_generated: float
    avg_order_value: float
    roi_multiplier: float
    net_revenue_gain: float

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Dashboard Models
# ============================================================================

class DashboardKPIsResponse(BaseModel):
    """Unified KPI dashboard."""
    churn_rate: float
    churn_rate_change: float
    avg_ltv: float
    ltv_change_pct: float
    cart_recovery_rate: float
    cart_recovery_revenue: float
    pricing_lift_pct: float
    total_interventions_cost: float
    total_incremental_revenue: float
    roi_multiplier: float
    last_updated_iso: str

    model_config = ConfigDict(from_attributes=True)


class InterventionHistoryResponse(BaseModel):
    """Historical intervention for a customer."""
    campaign_id: str
    campaign_type: str
    sent_at_iso: str
    converted: bool
    conversion_date_iso: Optional[str] = None
    order_value: Optional[float] = None


class UnifiedCustomerIntelligenceResponse(BaseModel):
    """Complete customer view across all modules."""
    customer_id: str
    churn_risk_score: float
    churn_tier: str
    ltv_90day: float
    ltv_365day: float
    ltv_tier: str
    abandoned_carts_count: int
    total_abandoned_value: float
    intervention_history: List[InterventionHistoryResponse]
    pricing_sensitivity: str
    recommended_strategy: str

    model_config = ConfigDict(from_attributes=True)


class SegmentAccuracyResponse(BaseModel):
    """Model accuracy breakdown by cohort."""
    segment_name: str
    accuracy_metric: float


class ModelPerformanceDashboardResponse(BaseModel):
    """Model performance metrics and drift detection."""
    churn_model_auc: float
    churn_model_auc_by_segment: List[SegmentAccuracyResponse]
    ltv_model_mae: float
    ltv_model_mae_by_cohort: List[SegmentAccuracyResponse]
    recovery_model_auc: float
    elasticity_accuracy: float
    drift_detected: bool
    drift_alert_msg: Optional[str] = None
    last_evaluated_iso: str

    model_config = ConfigDict(from_attributes=True)


class DataFreshnessResponse(BaseModel):
    """Timestamps and SLA status for data."""
    cassandra_last_refresh_minutes_ago: int
    iceberg_last_refresh_hours_ago: int
    churn_scores_last_computed_hours_ago: int
    ltv_predictions_last_computed_hours_ago: int
    pricing_recommendations_last_computed_hours_ago: int
    cassandra_sla_minutes: int
    iceberg_sla_hours: int
    within_sla: bool

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# System Models
# ============================================================================

class HealthDetailsResponse(BaseModel):
    """Detailed health check info."""
    cassandra: str
    presto: str
    model_files: str
    timestamp: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: str
    details: HealthDetailsResponse


# ============================================================================
# Request Models
# ============================================================================

class CreateChurnCampaignRequest(BaseModel):
    """Create churn intervention campaign."""
    customer_ids: List[str]
    intervention_type: str
    offer_details: Dict
    scheduled_send_time_iso: Optional[str] = None


class CreateRecoveryCampaignRequest(BaseModel):
    """Create cart recovery campaign."""
    cart_customer_product_pairs: List[Dict]
    offer_type: str
    offer_details: Dict
    scheduled_send_time_iso: Optional[str] = None


class CreateExperimentRequest(BaseModel):
    """Create pricing A/B test."""
    name: str
    treatments: List[Dict]
    metric: str
    start_date_iso: str
    end_date_iso: str
    sample_size_per_treatment: int = 1000


class ExportChurnRequest(BaseModel):
    """Export at-risk customers."""
    tier: Optional[str] = None
    limit: int = 1000
    include_columns: Optional[List[str]] = None


class ExportRecoveryCartsRequest(BaseModel):
    """Export recoverable carts."""
    tier: Optional[str] = None
    limit: int = 1000
    include_columns: Optional[List[str]] = None
