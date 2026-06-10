"""Customer Lifetime Value prediction routes."""

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_ltv_service
from src.models.schemas import (
    HighPotentialCustomerResponse,
    LTVCohortResponse,
    LTVFactorResponse,
    LTVPredictionsResponse,
    ModelAccuracyMetricsResponse,
    SegmentAccuracyResponse,
)
from src.services.ltv_service import LTVService

router = APIRouter(prefix="/api/v1/ltv", tags=["ltv"])


@router.get("/customer/{customer_id}/predictions", response_model=LTVPredictionsResponse)
async def get_ltv_predictions(
    customer_id: str,
    service: LTVService = Depends(get_ltv_service),
):
    """Get LTV predictions at multiple horizons (7d, 30d, 90d, 1y)."""
    predictions = service.predict_ltv(customer_id)
    if predictions is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    return LTVPredictionsResponse(
        customer_id=predictions.customer_id,
        ltv_7day=predictions.ltv_7day,
        ltv_30day=predictions.ltv_30day,
        ltv_90day=predictions.ltv_90day,
        ltv_365day=predictions.ltv_365day,
        factors=[
            LTVFactorResponse(
                factor=f["factor"],
                contribution_score=f["contribution_score"],
                description=f["description"],
            )
            for f in predictions.factors
        ],
    )


@router.get(
    "/customer/{customer_id}/value-drivers",
    response_model=list[LTVFactorResponse],
)
async def get_ltv_value_drivers(
    customer_id: str,
    service: LTVService = Depends(get_ltv_service),
):
    """Get LTV prediction factors (value drivers)."""
    predictions = service.predict_ltv(customer_id)
    if predictions is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    return [
        LTVFactorResponse(
            factor=f["factor"],
            contribution_score=f["contribution_score"],
            description=f["description"],
        )
        for f in predictions.factors
    ]


@router.get("/cohorts/high-value", response_model=list[LTVCohortResponse])
async def list_high_value_cohorts(
    limit: int = Query(20, ge=1, le=1000),
    service: LTVService = Depends(get_ltv_service),
):
    """List high-value customer cohorts."""
    cohorts = service.list_high_value_cohorts(limit=limit)
    return [
        LTVCohortResponse(
            cohort_name=c.cohort_name,
            size=c.size,
            avg_ltv=c.avg_ltv,
            avg_ltv_7day=c.avg_ltv_7day,
            avg_ltv_30day=c.avg_ltv_30day,
            avg_ltv_90day=c.avg_ltv_90day,
            avg_ltv_365day=c.avg_ltv_365day,
            characteristics=c.characteristics,
        )
        for c in cohorts
    ]


@router.get(
    "/customers/new-high-potential",
    response_model=list[HighPotentialCustomerResponse],
)
async def list_new_high_potential_customers(
    acquisition_hours: int = Query(168, ge=1),
    limit: int = Query(100, ge=1, le=10000),
    service: LTVService = Depends(get_ltv_service),
):
    """List new customers with high LTV potential."""
    customers = service.flag_new_high_potential(
        acquisition_hours=acquisition_hours,
        limit=limit,
    )
    return [
        HighPotentialCustomerResponse(
            customer_id=c.customer_id,
            days_as_customer=c.days_as_customer,
            predicted_ltv_90day=c.predicted_ltv_90day,
            confidence=c.confidence,
            signals=c.signals,
        )
        for c in customers
    ]


@router.get("/accuracy", response_model=ModelAccuracyMetricsResponse)
async def get_ltv_model_accuracy(
    historical_window_days: int = Query(90, ge=1),
    service: LTVService = Depends(get_ltv_service),
):
    """Get LTV model accuracy metrics."""
    metrics = service.get_model_accuracy(
        historical_window_days=historical_window_days,
    )
    if metrics is None:
        raise HTTPException(status_code=503, detail="Accuracy metrics unavailable")

    accuracy_by_cohort = [
        SegmentAccuracyResponse(
            segment_name=seg,
            accuracy_metric=acc,
        )
        for seg, acc in metrics.accuracy_by_cohort.items()
    ]

    return ModelAccuracyMetricsResponse(
        mean_absolute_error=metrics.mean_absolute_error,
        root_mean_squared_error=metrics.root_mean_squared_error,
        mean_absolute_percentage_error=metrics.mean_absolute_percentage_error,
        calibration_score=metrics.calibration_score,
        accuracy_by_cohort=accuracy_by_cohort,
    )
