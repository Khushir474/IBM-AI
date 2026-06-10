"""Churn prediction routes."""

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_churn_service
from src.models.schemas import (
    ChurnFactorResponse,
    ChurnInterventionResponse,
    ChurnRiskScoreResponse,
    PaginatedChurnResponse,
)
from src.services.churn_service import ChurnService, ChurnTier

router = APIRouter(prefix="/api/v1/churn", tags=["churn"])


@router.get("/customer/{customer_id}/risk-score", response_model=ChurnRiskScoreResponse)
async def get_churn_risk_score(
    customer_id: str,
    service: ChurnService = Depends(get_churn_service),
):
    """Get churn risk score for a customer."""
    score = service.score_customer(customer_id)
    if score is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    return ChurnRiskScoreResponse(
        customer_id=score.customer_id,
        score=score.score,
        tier=score.tier.name,
        factors=[
            ChurnFactorResponse(
                factor=f["factor"],
                contribution_score=f["contribution_score"],
                description=f["description"],
            )
            for f in score.factors
        ],
        recommended_intervention=ChurnInterventionResponse(
            intervention_type=score.recommended_intervention.intervention_type,
            description=score.recommended_intervention.description,
            recommended_discount=score.recommended_intervention.recommended_discount,
            confidence=score.recommended_intervention.confidence,
        ),
        confidence=score.confidence,
    )


@router.get("/customers", response_model=PaginatedChurnResponse)
async def list_churn_customers(
    churn_tier: str = Query(..., description="Churn tier: LOW, MEDIUM, or HIGH"),
    limit: int = Query(100, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    service: ChurnService = Depends(get_churn_service),
):
    """List customers by churn risk tier."""
    try:
        tier = ChurnTier[churn_tier.upper()]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid churn_tier. Must be one of: LOW, MEDIUM, HIGH",
        )

    scores, total = service.list_by_tier(tier=tier, limit=limit, offset=offset)

    return PaginatedChurnResponse(
        items=[
            ChurnRiskScoreResponse(
                customer_id=score.customer_id,
                score=score.score,
                tier=score.tier.name,
                factors=[
                    ChurnFactorResponse(
                        factor=f["factor"],
                        contribution_score=f["contribution_score"],
                        description=f["description"],
                    )
                    for f in score.factors
                ],
                recommended_intervention=ChurnInterventionResponse(
                    intervention_type=score.recommended_intervention.intervention_type,
                    description=score.recommended_intervention.description,
                    recommended_discount=score.recommended_intervention.recommended_discount,
                    confidence=score.recommended_intervention.confidence,
                ),
                confidence=score.confidence,
            )
            for score in scores
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/customer/{customer_id}/factors", response_model=list[ChurnFactorResponse])
async def get_churn_factors(
    customer_id: str,
    service: ChurnService = Depends(get_churn_service),
):
    """Get churn risk factors for a customer."""
    score = service.score_customer(customer_id)
    if score is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    return [
        ChurnFactorResponse(
            factor=f["factor"],
            contribution_score=f["contribution_score"],
            description=f["description"],
        )
        for f in score.factors
    ]
