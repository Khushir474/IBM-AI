"""Dashboard, analytics, and export routes."""

from fastapi import APIRouter, Depends, HTTPException, Response

from src.api.dependencies import (
    get_dashboard_service,
    get_export_service,
    get_churn_service,
    get_cart_service,
)
from src.models.schemas import (
    DashboardKPIsResponse,
    DataFreshnessResponse,
    ExportChurnRequest,
    ExportRecoveryCartsRequest,
    ModelPerformanceDashboardResponse,
    SegmentAccuracyResponse,
    UnifiedCustomerIntelligenceResponse,
    InterventionHistoryResponse,
)
from src.services.dashboard_service import DashboardService
from src.services.export_service import ExportService
from src.services.churn_service import ChurnService
from src.services.cart_service import CartService

router = APIRouter(tags=["dashboard"])


@router.get("/api/v1/dashboard/summary", response_model=DashboardKPIsResponse)
async def get_dashboard_summary(
    service: DashboardService = Depends(get_dashboard_service),
):
    """Get unified KPI dashboard."""
    kpis = service.get_kpi_summary()
    if kpis is None:
        raise HTTPException(status_code=503, detail="Dashboard data unavailable")

    return DashboardKPIsResponse(
        churn_rate=kpis.churn_rate,
        churn_rate_change=kpis.churn_rate_change,
        avg_ltv=kpis.avg_ltv,
        ltv_change_pct=kpis.ltv_change_pct,
        cart_recovery_rate=kpis.cart_recovery_rate,
        cart_recovery_revenue=kpis.cart_recovery_revenue,
        pricing_lift_pct=kpis.pricing_lift_pct,
        total_interventions_cost=kpis.total_interventions_cost,
        total_incremental_revenue=kpis.total_incremental_revenue,
        roi_multiplier=kpis.roi_multiplier,
        last_updated_iso=kpis.last_updated_iso,
    )


@router.get(
    "/api/v1/dashboard/customer/{customer_id}",
    response_model=UnifiedCustomerIntelligenceResponse,
)
async def get_customer_intelligence(
    customer_id: str,
    service: DashboardService = Depends(get_dashboard_service),
):
    """Get unified customer intelligence across all modules."""
    intelligence = service.get_customer_intelligence(customer_id)
    if intelligence is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    intervention_history = [
        InterventionHistoryResponse(
            campaign_id=ih["campaign_id"],
            campaign_type=ih["campaign_type"],
            sent_at_iso=ih["sent_at_iso"],
            converted=ih.get("converted", False),
            conversion_date_iso=ih.get("conversion_date_iso"),
            order_value=ih.get("order_value"),
        )
        for ih in intelligence.intervention_history
    ]

    return UnifiedCustomerIntelligenceResponse(
        customer_id=intelligence.customer_id,
        churn_risk_score=intelligence.churn_risk_score,
        churn_tier=intelligence.churn_tier,
        ltv_90day=intelligence.ltv_90day,
        ltv_365day=intelligence.ltv_365day,
        ltv_tier=intelligence.ltv_tier,
        abandoned_carts_count=intelligence.abandoned_carts_count,
        total_abandoned_value=intelligence.total_abandoned_value,
        intervention_history=intervention_history,
        pricing_sensitivity=intelligence.pricing_sensitivity,
        recommended_strategy=intelligence.recommended_strategy,
    )


@router.post("/api/v1/exports/churn-customers")
async def export_churn_customers(
    request: ExportChurnRequest,
    churn_service: ChurnService = Depends(get_churn_service),
    export_service: ExportService = Depends(get_export_service),
):
    """Export at-risk customers as CSV."""
    # Get churn customers by tier
    if request.tier:
        scores, _ = churn_service.list_by_tier(
            tier=request.tier,
            limit=request.limit,
            offset=0,
        )
    else:
        # Export all tiers
        scores = []
        for tier in ["LOW", "MEDIUM", "HIGH"]:
            tier_scores, _ = churn_service.list_by_tier(
                tier=tier,
                limit=request.limit,
                offset=0,
            )
            scores.extend(tier_scores)

    # Convert to dicts for export
    score_dicts = [
        {
            "customer_id": s.customer_id,
            "score": s.score,
            "tier": s.tier.name,
            "confidence": s.confidence,
        }
        for s in scores
    ]

    csv_content = export_service.export_churn_customers(
        score_dicts,
        include_columns=request.include_columns,
    )

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=churn_customers.csv"},
    )


@router.post("/api/v1/exports/recovery-carts")
async def export_recovery_carts(
    request: ExportRecoveryCartsRequest,
    cart_service: CartService = Depends(get_cart_service),
    export_service: ExportService = Depends(get_export_service),
):
    """Export recoverable carts as CSV."""
    carts = cart_service.detect_abandoned_carts(
        recovery_tier=request.tier,
        limit=request.limit,
        offset=0,
    )

    # Convert to dicts for export
    cart_dicts = [
        {
            "customer_id": c.customer_id,
            "product_id": c.product_id,
            "cart_value": c.cart_value,
            "recovery_score": c.recovery_score,
            "recovery_tier": c.recovery_tier.name,
        }
        for c in carts
    ]

    csv_content = export_service.export_recovery_carts(
        cart_dicts,
        include_columns=request.include_columns,
    )

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=recovery_carts.csv"},
    )


@router.get(
    "/api/v1/models/performance",
    response_model=ModelPerformanceDashboardResponse,
)
async def get_model_performance(
    service: DashboardService = Depends(get_dashboard_service),
):
    """Get model performance metrics and drift detection."""
    perf = service.get_model_performance()
    if perf is None:
        raise HTTPException(status_code=503, detail="Model performance data unavailable")

    churn_by_segment = [
        SegmentAccuracyResponse(
            segment_name=seg,
            accuracy_metric=acc,
        )
        for seg, acc in perf.churn_model_auc_by_segment.items()
    ]

    ltv_by_cohort = [
        SegmentAccuracyResponse(
            segment_name=cohort,
            accuracy_metric=acc,
        )
        for cohort, acc in perf.ltv_model_mae_by_cohort.items()
    ]

    return ModelPerformanceDashboardResponse(
        churn_model_auc=perf.churn_model_auc,
        churn_model_auc_by_segment=churn_by_segment,
        ltv_model_mae=perf.ltv_model_mae,
        ltv_model_mae_by_cohort=ltv_by_cohort,
        recovery_model_auc=perf.recovery_model_auc,
        elasticity_accuracy=perf.elasticity_accuracy,
        drift_detected=perf.drift_detected,
        drift_alert_msg=perf.drift_alert_msg,
        last_evaluated_iso=perf.last_evaluated_iso,
    )


@router.get("/api/v1/system/data-freshness", response_model=DataFreshnessResponse)
async def get_data_freshness(
    service: DashboardService = Depends(get_dashboard_service),
):
    """Get data freshness and SLA status."""
    freshness = service.get_data_freshness()
    if freshness is None:
        raise HTTPException(status_code=503, detail="Freshness data unavailable")

    return DataFreshnessResponse(
        cassandra_last_refresh_minutes_ago=freshness.cassandra_last_refresh_minutes_ago,
        iceberg_last_refresh_hours_ago=freshness.iceberg_last_refresh_hours_ago,
        churn_scores_last_computed_hours_ago=freshness.churn_scores_last_computed_hours_ago,
        ltv_predictions_last_computed_hours_ago=freshness.ltv_predictions_last_computed_hours_ago,
        pricing_recommendations_last_computed_hours_ago=freshness.pricing_recommendations_last_computed_hours_ago,
        cassandra_sla_minutes=freshness.cassandra_sla_minutes,
        iceberg_sla_hours=freshness.iceberg_sla_hours,
        within_sla=freshness.within_sla,
    )
