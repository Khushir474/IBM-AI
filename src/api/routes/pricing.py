"""Dynamic pricing and A/B testing routes."""

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import (
    get_pricing_service,
    get_experiment_service,
)
from src.models.schemas import (
    CreateExperimentRequest,
    ElasticityEstimateResponse,
    ExperimentResponse,
    ExperimentResultsResponse,
    PriceRecommendationResponse,
    TreatmentResultResponse,
)
from src.services.pricing_service import PricingService
from src.services.experiment_service import ExperimentService

router = APIRouter(prefix="/api/v1/pricing", tags=["pricing"])


@router.get(
    "/products/{product_id}/recommendation",
    response_model=PriceRecommendationResponse,
)
async def get_price_recommendation(
    product_id: str,
    service: PricingService = Depends(get_pricing_service),
):
    """Get price/discount recommendation for a product."""
    recommendation = service.recommend_price(product_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return PriceRecommendationResponse(
        product_id=recommendation.product_id,
        current_price=recommendation.current_price,
        recommended_price=recommendation.recommended_price,
        discount_pct=recommendation.discount_pct,
        expected_revenue_impact=recommendation.expected_revenue_impact,
        margin_impact=recommendation.margin_impact,
        confidence=recommendation.confidence,
        reason=recommendation.reason,
    )


@router.get(
    "/dashboard",
    response_model=list[PriceRecommendationResponse],
)
async def get_pricing_dashboard(
    category: str = Query(None, description="Filter by category"),
    min_revenue_impact: float = Query(None, description="Min revenue impact threshold"),
    limit: int = Query(20, ge=1, le=1000),
    service: PricingService = Depends(get_pricing_service),
):
    """Get all pricing recommendations ranked by revenue impact."""
    # TODO: Phase 6 will fetch real recommendations from pricing DAO
    # For now, return empty list (service will be wired to real data)
    return []


@router.get(
    "/elasticity",
    response_model=list[ElasticityEstimateResponse],
)
async def get_elasticity_estimates(
    product_id: str = Query(None, description="Filter by product"),
    service: PricingService = Depends(get_pricing_service),
):
    """Get price elasticity estimates."""
    # TODO: Phase 6 will fetch real elasticity estimates
    # For now, return empty list
    return []


@router.post("/experiments", response_model=ExperimentResponse, status_code=201)
async def create_experiment(
    request: CreateExperimentRequest,
    service: ExperimentService = Depends(get_experiment_service),
):
    """Create a pricing A/B test experiment."""
    experiment = service.create_discount_experiment(
        name=request.name,
        treatments=request.treatments,
        metric=request.metric,
        start_date_iso=request.start_date_iso,
        end_date_iso=request.end_date_iso,
        sample_size_per_treatment=request.sample_size_per_treatment,
    )

    return ExperimentResponse(
        experiment_id=experiment.experiment_id,
        name=experiment.name,
        treatments=experiment.treatments,
        metric=experiment.metric,
        start_date_iso=experiment.start_date_iso,
        end_date_iso=experiment.end_date_iso,
        status=experiment.status,
        sample_size_per_treatment=experiment.sample_size_per_treatment,
    )


@router.get(
    "/experiments/{experiment_id}/results",
    response_model=ExperimentResultsResponse,
)
async def get_experiment_results(
    experiment_id: str,
    service: ExperimentService = Depends(get_experiment_service),
):
    """Get A/B test results with statistical significance."""
    # TODO: Phase 6 will fetch real experiment data from DAO
    # For now, return placeholder
    results = service.analyze_experiment_results(
        experiment_id,
        treatment_data={},
    )

    if results is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    treatment_results = [
        TreatmentResultResponse(
            treatment_name=tr["treatment_name"],
            conversion_rate=tr.get("conversion_rate", 0.0),
            sample_size=tr.get("sample_size", 0),
            mean_order_value=tr.get("mean_order_value"),
        )
        for tr in results.treatment_results
    ]

    return ExperimentResultsResponse(
        experiment_id=results.experiment_id,
        treatment_results=treatment_results,
        winner=results.winner,
        p_value=results.p_value,
        significant_at_95=results.significant_at_95,
        recommendation=results.recommendation,
    )
