"""Campaign and intervention service (Task 3.5)."""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class CampaignType(str, Enum):
    """Type of campaign."""

    CHURN = "churn_intervention"
    CART_RECOVERY = "cart_recovery"
    LTV_NURTURE = "ltv_nurture"
    PRICING = "pricing_promotion"


@dataclass
class Campaign:
    """Campaign record."""

    campaign_id: str
    campaign_type: CampaignType
    created_at_iso: str
    audience_count: int
    offer_details: Dict  # {type, discount_pct, free_shipping, etc}
    status: str  # draft, active, completed
    scheduled_send_time_iso: Optional[str] = None


@dataclass
class CampaignSend:
    """Record of campaign send."""

    campaign_id: str
    customer_id: str
    sent_at_iso: str
    offer_code: str
    offer_details: Dict


@dataclass
class CampaignResult:
    """Campaign effectiveness metrics."""

    campaign_id: str
    total_sent: int
    total_converted: int
    conversion_rate: float  # %
    total_revenue_generated: float
    avg_order_value: float
    roi_multiplier: float  # revenue / discount_cost
    net_revenue_gain: float  # After discount cost


class CampaignService:
    """Business logic for campaign creation, tracking, and effectiveness measurement."""

    def __init__(self, campaign_dao=None):
        """Initialize CampaignService.

        Args:
            campaign_dao: Optional DAO for Cassandra campaign tables
        """
        self.campaign_dao = campaign_dao

    def create_churn_campaign(
        self,
        customer_ids: List[str],
        intervention_type: str,
        offer_details: Dict,
        scheduled_send_time_iso: Optional[str] = None,
    ) -> Campaign:
        """Create churn intervention campaign.

        Args:
            customer_ids: List of at-risk customer IDs
            intervention_type: "email_offer", "vip_upgrade", "product_recommendation"
            offer_details: {discount_pct, free_shipping, product_ids, etc}
            scheduled_send_time_iso: When to send (optional)

        Returns:
            Campaign record

        REQ-004, REQ-005: Create churn campaign
        """
        campaign_id = f"camp_{datetime.utcnow().isoformat()}_churn"

        campaign = Campaign(
            campaign_id=campaign_id,
            campaign_type=CampaignType.CHURN,
            created_at_iso=datetime.utcnow().isoformat(),
            audience_count=len(customer_ids),
            offer_details=offer_details,
            status="draft",
            scheduled_send_time_iso=scheduled_send_time_iso,
        )

        logger.info(
            f"Created churn campaign {campaign_id} for {len(customer_ids)} customers"
        )
        return campaign

    def create_recovery_campaign(
        self,
        cart_items: List[Dict],
        offer_type: str,
        offer_details: Dict,
        scheduled_send_time_iso: Optional[str] = None,
    ) -> Campaign:
        """Create cart recovery campaign.

        Args:
            cart_items: List of {customer_id, product_id, cart_value}
            offer_type: "discount", "free_shipping", "bundle"
            offer_details: {discount_pct, offer_code, etc}
            scheduled_send_time_iso: When to send

        Returns:
            Campaign record

        REQ-013, REQ-015: Create recovery campaign
        """
        campaign_id = f"camp_{datetime.utcnow().isoformat()}_recovery"

        campaign = Campaign(
            campaign_id=campaign_id,
            campaign_type=CampaignType.CART_RECOVERY,
            created_at_iso=datetime.utcnow().isoformat(),
            audience_count=len(cart_items),
            offer_details=offer_details,
            status="draft",
            scheduled_send_time_iso=scheduled_send_time_iso,
        )

        logger.info(
            f"Created recovery campaign {campaign_id} for {len(cart_items)} carts"
        )
        return campaign

    def track_send(
        self,
        campaign_id: str,
        customer_id: str,
        offer_code: str,
        offer_details: Dict,
    ):
        """Record campaign send event.

        Args:
            campaign_id: Campaign ID
            customer_id: Customer ID
            offer_code: Code sent to customer
            offer_details: Offer details from campaign

        REQ-005, REQ-015: Track send
        """
        send_record = CampaignSend(
            campaign_id=campaign_id,
            customer_id=customer_id,
            sent_at_iso=datetime.utcnow().isoformat(),
            offer_code=offer_code,
            offer_details=offer_details,
        )

        logger.info(f"Tracked send for {campaign_id}/{customer_id}")
        return send_record

    def track_conversion(
        self,
        campaign_id: str,
        customer_id: str,
        converted: bool,
        conversion_date_iso: str,
        order_value: Optional[float] = None,
    ):
        """Record conversion from campaign.

        Args:
            campaign_id: Campaign ID
            customer_id: Customer ID
            converted: Did customer convert?
            conversion_date_iso: When did they convert?
            order_value: Order value if converted

        REQ-005, REQ-015: Track conversion
        """
        result = {
            "campaign_id": campaign_id,
            "customer_id": customer_id,
            "converted": converted,
            "conversion_date": conversion_date_iso,
            "order_value": order_value or 0.0,
        }

        logger.info(
            f"Tracked conversion for {campaign_id}/{customer_id}: converted={converted}"
        )
        return result

    def measure_campaign_effectiveness(
        self,
        campaign_id: str,
        sends: List[Dict],
        conversions: List[Dict],
    ) -> CampaignResult:
        """Measure campaign effectiveness with lift calculation.

        Args:
            campaign_id: Campaign ID
            sends: List of send records {customer_id, sent_at, offer_details}
            conversions: List of conversion records {customer_id, converted, order_value}

        Returns:
            CampaignResult with conversion rate, revenue, ROI

        REQ-005, REQ-015: Measure effectiveness
        """
        total_sent = len(sends)
        if total_sent == 0:
            return CampaignResult(
                campaign_id=campaign_id,
                total_sent=0,
                total_converted=0,
                conversion_rate=0.0,
                total_revenue_generated=0.0,
                avg_order_value=0.0,
                roi_multiplier=0.0,
                net_revenue_gain=0.0,
            )

        # Count conversions
        converted_records = [c for c in conversions if c.get("converted")]
        total_converted = len(converted_records)
        conversion_rate = (total_converted / total_sent) * 100

        # Calculate revenue
        total_revenue = sum(c.get("order_value", 0) for c in converted_records)
        avg_order_value = total_revenue / total_converted if total_converted > 0 else 0

        # Calculate discount cost (simplified: assume 15% discount on revenue)
        discount_cost = total_revenue * 0.15
        net_revenue_gain = total_revenue - discount_cost

        # Calculate ROI
        roi_multiplier = (total_revenue / discount_cost) if discount_cost > 0 else 0

        return CampaignResult(
            campaign_id=campaign_id,
            total_sent=total_sent,
            total_converted=total_converted,
            conversion_rate=conversion_rate,
            total_revenue_generated=total_revenue,
            avg_order_value=avg_order_value,
            roi_multiplier=roi_multiplier,
            net_revenue_gain=net_revenue_gain,
        )

    def measure_ab_test_comparison(
        self,
        campaign_id: str,
        treatment_conversions: Dict[str, List[Dict]],
    ) -> Dict:
        """Compare A/B test treatments.

        Args:
            campaign_id: Campaign ID
            treatment_conversions: {treatment_name: [conversion records]}

        Returns:
            Dict comparing treatments {treatment: {sent, converted, rate, winner: bool}}
        """
        comparison = {}

        for treatment_name, conversions in treatment_conversions.items():
            converted = sum(1 for c in conversions if c.get("converted"))
            total = len(conversions)
            conversion_rate = (converted / total * 100) if total > 0 else 0

            comparison[treatment_name] = {
                "total_sent": total,
                "conversions": converted,
                "conversion_rate": conversion_rate,
            }

        # Find winner (highest conversion rate)
        if comparison:
            winner = max(comparison.items(), key=lambda x: x[1]["conversion_rate"])
            comparison[winner[0]]["winner"] = True

        return comparison
