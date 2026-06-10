"""Cart abandonment and recovery routes."""

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_cart_service
from src.models.schemas import (
    AbandonedCartResponse,
    AbandonmentFactorResponse,
    RecoveryOfferResponse,
)
from src.services.cart_service import CartService, RecoveryTier

router = APIRouter(prefix="/api/v1/carts", tags=["carts"])


@router.get("/abandoned", response_model=list[AbandonedCartResponse])
async def list_abandoned_carts(
    recovery_tier: str = Query(None, description="Recovery tier: HIGH, MEDIUM, or LOW"),
    limit: int = Query(100, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    idle_minutes: int = Query(60, ge=1),
    service: CartService = Depends(get_cart_service),
):
    """List abandoned carts by recovery potential."""
    tier = None
    if recovery_tier:
        try:
            tier = RecoveryTier[recovery_tier.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid recovery_tier. Must be one of: HIGH, MEDIUM, LOW",
            )

    carts = service.detect_abandoned_carts(
        idle_minutes=idle_minutes,
        recovery_tier=tier,
        limit=limit,
        offset=offset,
    )

    return [
        AbandonedCartResponse(
            customer_id=cart.customer_id,
            product_id=cart.product_id,
            cart_value=cart.cart_value,
            item_count=cart.item_count,
            abandon_time_iso=cart.abandon_time_iso,
            recovery_score=cart.recovery_score,
            recovery_tier=cart.recovery_tier.name,
            factors=[
                AbandonmentFactorResponse(
                    factor=f["factor"],
                    contribution_score=f["contribution_score"],
                    description=f["description"],
                )
                for f in cart.factors
            ],
            recommended_offer=(
                {
                    "offer_type": cart.recommended_offer.offer_type,
                    "discount_pct": cart.recommended_offer.discount_pct,
                    "free_shipping": cart.recommended_offer.free_shipping,
                    "conversion_probability": cart.recommended_offer.conversion_probability,
                }
                if cart.recommended_offer
                else None
            ),
        )
        for cart in carts
    ]


@router.get(
    "/{customer_id}/{product_id}/abandonment",
    response_model=AbandonedCartResponse,
)
async def get_abandonment_details(
    customer_id: str,
    product_id: str,
    service: CartService = Depends(get_cart_service),
):
    """Get abandonment details and recovery factors for a cart."""
    carts = service.detect_abandoned_carts(limit=10000)
    matching_cart = next(
        (c for c in carts if c.customer_id == customer_id and c.product_id == product_id),
        None,
    )

    if matching_cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")

    return AbandonedCartResponse(
        customer_id=matching_cart.customer_id,
        product_id=matching_cart.product_id,
        cart_value=matching_cart.cart_value,
        item_count=matching_cart.item_count,
        abandon_time_iso=matching_cart.abandon_time_iso,
        recovery_score=matching_cart.recovery_score,
        recovery_tier=matching_cart.recovery_tier.name,
        factors=[
            AbandonmentFactorResponse(
                factor=f["factor"],
                contribution_score=f["contribution_score"],
                description=f["description"],
            )
            for f in matching_cart.factors
        ],
        recommended_offer=(
            {
                "offer_type": matching_cart.recommended_offer.offer_type,
                "discount_pct": matching_cart.recommended_offer.discount_pct,
                "free_shipping": matching_cart.recommended_offer.free_shipping,
                "conversion_probability": matching_cart.recommended_offer.conversion_probability,
            }
            if matching_cart.recommended_offer
            else None
        ),
    )


@router.get(
    "/{customer_id}/{product_id}/recovery-offer",
    response_model=RecoveryOfferResponse,
)
async def get_recovery_offer(
    customer_id: str,
    product_id: str,
    service: CartService = Depends(get_cart_service),
):
    """Get recommended recovery offer for an abandoned cart."""
    offer = service.recommend_recovery_offer(customer_id, product_id)
    if offer is None:
        raise HTTPException(status_code=404, detail="Cart or offer not found")

    return RecoveryOfferResponse(
        offer_type=offer.offer_type,
        discount_pct=offer.discount_pct,
        free_shipping=offer.free_shipping,
        conversion_probability=offer.conversion_probability,
    )
