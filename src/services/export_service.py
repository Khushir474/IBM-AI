"""Export service for CSV generation (Task 3.8)."""

import logging
import csv
from io import StringIO
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class ExportService:
    """Business logic for exporting insights and campaign data."""

    def __init__(self, churn_service=None, cart_service=None):
        """Initialize ExportService.

        Args:
            churn_service: ChurnService instance
            cart_service: CartService instance
        """
        self.churn_service = churn_service
        self.cart_service = cart_service

    def export_churn_customers(
        self,
        churn_scores: List[Dict],
        include_columns: Optional[List[str]] = None,
    ) -> str:
        """Export churn risk customers to CSV.

        Args:
            churn_scores: List of ChurnRiskScore dicts
            include_columns: Specific columns to include (or None for all)

        Returns:
            CSV string (can be written to file or sent to Klaviyo)

        REQ-029: Export and Integration
        """
        if not churn_scores:
            logger.warning("No churn scores to export")
            return ""

        # Default columns
        default_columns = [
            "customer_id",
            "churn_score",
            "churn_tier",
            "ltv_90day",
            "top_factor_1",
            "top_factor_2",
            "recommended_intervention",
            "export_timestamp",
        ]
        columns = include_columns or default_columns

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()

        from datetime import datetime

        for score in churn_scores:
            row = {
                "customer_id": score.get("customer_id", ""),
                "churn_score": score.get("score", ""),
                "churn_tier": score.get("tier", ""),
                "ltv_90day": score.get("ltv_90day", ""),
                "top_factor_1": (
                    score.get("factors", [{}])[0].get("description", "")
                    if score.get("factors")
                    else ""
                ),
                "top_factor_2": (
                    score.get("factors", [{}, {}])[1].get("description", "")
                    if len(score.get("factors", [])) > 1
                    else ""
                ),
                "recommended_intervention": score.get("recommended_intervention", ""),
                "export_timestamp": datetime.utcnow().isoformat(),
            }

            # Only include requested columns
            filtered_row = {k: v for k, v in row.items() if k in columns}
            writer.writerow(filtered_row)

        csv_content = output.getvalue()
        logger.info(f"Exported {len(churn_scores)} churn customers to CSV")
        return csv_content

    def export_recovery_carts(
        self,
        abandoned_carts: List[Dict],
        include_columns: Optional[List[str]] = None,
    ) -> str:
        """Export abandoned carts for recovery to CSV.

        Args:
            abandoned_carts: List of AbandonedCart dicts
            include_columns: Specific columns to include (or None for all)

        Returns:
            CSV string

        REQ-029: Export and Integration
        """
        if not abandoned_carts:
            logger.warning("No carts to export")
            return ""

        # Default columns
        default_columns = [
            "customer_id",
            "product_id",
            "cart_value",
            "recovery_score",
            "recovery_tier",
            "recommended_offer_type",
            "recommended_discount_pct",
            "expected_conversion_prob",
            "export_timestamp",
        ]
        columns = include_columns or default_columns

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()

        from datetime import datetime

        for cart in abandoned_carts:
            offer = cart.get("recommended_offer", {})
            row = {
                "customer_id": cart.get("customer_id", ""),
                "product_id": cart.get("product_id", ""),
                "cart_value": cart.get("cart_value", ""),
                "recovery_score": cart.get("recovery_score", ""),
                "recovery_tier": cart.get("recovery_tier", ""),
                "recommended_offer_type": offer.get("type", ""),
                "recommended_discount_pct": offer.get("discount_pct", ""),
                "expected_conversion_prob": offer.get("conversion_prob", ""),
                "export_timestamp": datetime.utcnow().isoformat(),
            }

            # Only include requested columns
            filtered_row = {k: v for k, v in row.items() if k in columns}
            writer.writerow(filtered_row)

        csv_content = output.getvalue()
        logger.info(f"Exported {len(abandoned_carts)} carts to CSV")
        return csv_content

    def export_campaign_results(
        self,
        campaign_results: List[Dict],
        include_columns: Optional[List[str]] = None,
    ) -> str:
        """Export campaign effectiveness results to CSV.

        Args:
            campaign_results: List of CampaignResult dicts
            include_columns: Specific columns to include

        Returns:
            CSV string

        REQ-029: Export and Integration
        """
        if not campaign_results:
            logger.warning("No campaign results to export")
            return ""

        default_columns = [
            "campaign_id",
            "total_sent",
            "total_converted",
            "conversion_rate_pct",
            "total_revenue",
            "avg_order_value",
            "roi_multiplier",
            "net_revenue_gain",
        ]
        columns = include_columns or default_columns

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()

        for result in campaign_results:
            row = {
                "campaign_id": result.get("campaign_id", ""),
                "total_sent": result.get("total_sent", ""),
                "total_converted": result.get("total_converted", ""),
                "conversion_rate_pct": f"{result.get('conversion_rate', 0):.2f}",
                "total_revenue": f"${result.get('total_revenue', 0):.2f}",
                "avg_order_value": f"${result.get('avg_order_value', 0):.2f}",
                "roi_multiplier": f"{result.get('roi_multiplier', 0):.2f}x",
                "net_revenue_gain": f"${result.get('net_revenue_gain', 0):.2f}",
            }

            filtered_row = {k: v for k, v in row.items() if k in columns}
            writer.writerow(filtered_row)

        csv_content = output.getvalue()
        logger.info(f"Exported {len(campaign_results)} campaign results to CSV")
        return csv_content

    def export_pricing_recommendations(
        self,
        recommendations: List[Dict],
        include_columns: Optional[List[str]] = None,
    ) -> str:
        """Export pricing recommendations to CSV.

        Args:
            recommendations: List of PriceRecommendation dicts
            include_columns: Specific columns to include

        Returns:
            CSV string

        REQ-029: Export and Integration
        """
        if not recommendations:
            logger.warning("No pricing recommendations to export")
            return ""

        default_columns = [
            "product_id",
            "current_price",
            "recommended_price",
            "discount_pct",
            "expected_revenue_impact_daily",
            "margin_pct",
            "confidence",
            "reason",
        ]
        columns = include_columns or default_columns

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()

        for rec in recommendations:
            impact = rec.get("expected_revenue_impact", {})
            row = {
                "product_id": rec.get("product_id", ""),
                "current_price": f"${rec.get('current_price', 0):.2f}",
                "recommended_price": f"${rec.get('recommended_price', 0):.2f}",
                "discount_pct": f"{rec.get('discount_pct', 0):.1f}%",
                "expected_revenue_impact_daily": f"${impact.get('revenue_change_daily', 0):.2f}",
                "margin_pct": f"{rec.get('margin_impact', 0):.1f}%",
                "confidence": f"{rec.get('confidence', 0):.2f}",
                "reason": rec.get("reason", ""),
            }

            filtered_row = {k: v for k, v in row.items() if k in columns}
            writer.writerow(filtered_row)

        csv_content = output.getvalue()
        logger.info(f"Exported {len(recommendations)} pricing recommendations to CSV")
        return csv_content
