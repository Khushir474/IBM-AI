"""Campaign management and effectiveness tracking routes."""

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_campaign_service
from src.models.schemas import (
    CampaignResponse,
    CampaignResultsResponse,
    CreateChurnCampaignRequest,
    CreateRecoveryCampaignRequest,
)
from src.services.campaign_service import CampaignService

router = APIRouter(prefix="/api/v1/campaigns", tags=["campaigns"])


@router.post("/churn", response_model=CampaignResponse, status_code=201)
async def create_churn_campaign(
    request: CreateChurnCampaignRequest,
    service: CampaignService = Depends(get_campaign_service),
):
    """Create churn intervention campaign."""
    campaign = service.create_churn_campaign(
        customer_ids=request.customer_ids,
        intervention_type=request.intervention_type,
        offer_details=request.offer_details,
        scheduled_send_time_iso=request.scheduled_send_time_iso,
    )

    if campaign is None:
        raise HTTPException(status_code=400, detail="Failed to create campaign")

    return CampaignResponse(
        campaign_id=campaign.campaign_id,
        campaign_type=campaign.campaign_type,
        created_at_iso=campaign.created_at_iso,
        audience_count=campaign.audience_count,
        offer_details=campaign.offer_details,
        status=campaign.status,
        scheduled_send_time_iso=campaign.scheduled_send_time_iso,
    )


@router.post("/recovery", response_model=CampaignResponse, status_code=201)
async def create_recovery_campaign(
    request: CreateRecoveryCampaignRequest,
    service: CampaignService = Depends(get_campaign_service),
):
    """Create cart recovery campaign."""
    campaign = service.create_recovery_campaign(
        cart_items=request.cart_customer_product_pairs,
        offer_type=request.offer_type,
        offer_details=request.offer_details,
        scheduled_send_time_iso=request.scheduled_send_time_iso,
    )

    if campaign is None:
        raise HTTPException(status_code=400, detail="Failed to create campaign")

    return CampaignResponse(
        campaign_id=campaign.campaign_id,
        campaign_type=campaign.campaign_type,
        created_at_iso=campaign.created_at_iso,
        audience_count=campaign.audience_count,
        offer_details=campaign.offer_details,
        status=campaign.status,
        scheduled_send_time_iso=campaign.scheduled_send_time_iso,
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    service: CampaignService = Depends(get_campaign_service),
):
    """Get campaign status and details."""
    # TODO: Phase 6 will fetch from campaign DAO
    # For now, return placeholder or None
    raise HTTPException(status_code=404, detail="Campaign not found")


@router.get("/{campaign_id}/results", response_model=CampaignResultsResponse)
async def get_campaign_results(
    campaign_id: str,
    service: CampaignService = Depends(get_campaign_service),
):
    """Get campaign results, ROI, and conversion metrics."""
    # TODO: Phase 6 will fetch real send/conversion data and call measure_campaign_effectiveness
    # For now, return placeholder or None
    raise HTTPException(status_code=404, detail="Campaign results not found")
