"""LTV Feature Engineering.

Compute 7 LTV prediction features from Cassandra + Iceberg data:
1. historical_ltv — from customers.current_ltv (Cassandra) or customer_ltv_monthly (Iceberg)
2. cohort_avg_ltv — from cohort_retention (Iceberg) + acquisition cohort
3. cumulative_orders — from customers.total_orders (Cassandra)
4. product_category_spend — from orders_archive (Iceberg)
5. repeat_purchase_rate — from orders_archive (Iceberg)
6. seasonality_index — from daily_sales_summary (Iceberg)
7. loyalty_tier — from customers.loyalty_tier (Cassandra)
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from dataclasses import dataclass

import structlog

from src.data.daos.cassandra_daos import CustomerDAO, OrderDAO
from src.data.daos.iceberg_daos import CustomerLTVDAO, DailySalesSummaryDAO

logger = structlog.get_logger(__name__)


@dataclass
class LTVFeatures:
    """LTV prediction feature vector."""

    customer_id: UUID
    historical_ltv: float
    cohort_avg_ltv: float
    cumulative_orders: int
    product_category_spend: Dict[str, float]
    repeat_purchase_rate: float
    seasonality_index: float
    loyalty_tier: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for ML model input."""
        return {
            "customer_id": str(self.customer_id),
            "historical_ltv": self.historical_ltv,
            "cohort_avg_ltv": self.cohort_avg_ltv,
            "cumulative_orders": self.cumulative_orders,
            "product_category_spend": self.product_category_spend,
            "repeat_purchase_rate": self.repeat_purchase_rate,
            "seasonality_index": self.seasonality_index,
            "loyalty_tier": self.loyalty_tier,
        }


class LTVFeatureEngineer:
    """Compute LTV prediction features from multiple data sources."""

    LOYALTY_TIER_MAPPING = {
        "PLATINUM": 1.0,
        "GOLD": 0.8,
        "SILVER": 0.6,
        "BRONZE": 0.4,
        "NONE": 0.0,
    }

    def __init__(
        self,
        customer_dao: CustomerDAO,
        order_dao: OrderDAO,
        customer_ltv_dao: CustomerLTVDAO,
        daily_sales_dao: DailySalesSummaryDAO,
    ):
        """Initialize LTVFeatureEngineer.

        Args:
            customer_dao: CustomerDAO for customer profiles
            order_dao: OrderDAO for order history
            customer_ltv_dao: CustomerLTVDAO for LTV snapshots
            daily_sales_dao: DailySalesSummaryDAO for sales trends
        """
        self.customer_dao = customer_dao
        self.order_dao = order_dao
        self.customer_ltv_dao = customer_ltv_dao
        self.daily_sales_dao = daily_sales_dao

    async def compute_features(self, customer_id: UUID) -> LTVFeatures:
        """Compute complete LTV feature vector for customer.

        Args:
            customer_id: Customer UUID

        Returns:
            LTVFeatures dataclass with all 7 features
        """
        # Get customer profile (Cassandra)
        customer = await self.customer_dao.get_customer(customer_id)
        if not customer:
            logger.warning("customer_not_found", customer_id=customer_id)
            return self._default_features(customer_id)

        # Get latest LTV snapshot (Iceberg)
        ltv_snapshot = await self.customer_ltv_dao.get_latest_customer_ltv(
            str(customer_id)
        )

        # Get order history for category spend
        orders = await self.order_dao.get_inflight_orders(customer_id, limit=100)

        # Get daily sales for seasonality index
        now = datetime.utcnow()
        date_range = (
            (now - timedelta(days=90)).date(),
            now.date(),
        )
        daily_sales = await self.daily_sales_dao.get_daily_revenue(date_range)

        # Compute individual features
        historical_ltv = self._compute_historical_ltv(customer)
        cohort_avg_ltv = self._compute_cohort_avg_ltv(customer)
        cumulative_orders = self._compute_cumulative_orders(customer)
        category_spend = self._compute_product_category_spend(orders)
        repeat_purchase = self._compute_repeat_purchase_rate(
            customer.get("total_orders", 0),
            customer.get("multi_item_orders", 0),
        )
        seasonality = self._compute_seasonality_index(daily_sales)
        loyalty = self._compute_loyalty_tier_feature(customer)

        features = LTVFeatures(
            customer_id=customer_id,
            historical_ltv=historical_ltv,
            cohort_avg_ltv=cohort_avg_ltv,
            cumulative_orders=cumulative_orders,
            product_category_spend=category_spend,
            repeat_purchase_rate=repeat_purchase,
            seasonality_index=seasonality,
            loyalty_tier=loyalty,
        )

        logger.info(
            "ltv_features_computed",
            customer_id=customer_id,
            historical_ltv=historical_ltv,
            cumulative_orders=cumulative_orders,
        )

        return features

    def _compute_historical_ltv(self, customer: Dict) -> float:
        """Compute historical LTV from customer profile.

        Feature 1: What is the customer's current/historical LTV?
        """
        return float(customer.get("current_ltv", 0.0))

    def _compute_cohort_avg_ltv(self, customer: Dict) -> float:
        """Compute average LTV for customer's cohort.

        Feature 2: How does customer's cohort perform?
        Would query cohort_retention from Iceberg
        """
        # Simplified: return default cohort average
        # In production: query cohort_retention by acquisition month
        return 1500.0

    def _compute_cumulative_orders(self, customer: Dict) -> int:
        """Compute cumulative order count.

        Feature 3: How many orders has customer placed?
        """
        return int(customer.get("total_orders", 0))

    def _compute_product_category_spend(self, orders: List[Dict]) -> Dict[str, float]:
        """Compute spend by product category.

        Feature 4: What categories does customer prefer (spend)?
        """
        # Simplified: return empty dict
        # In production: would aggregate by category from orders
        return {}

    def _compute_repeat_purchase_rate(
        self, total_orders: int, multi_item_orders: int
    ) -> float:
        """Compute repeat purchase rate.

        Feature 5: Does customer make repeat purchases (multi-item orders)?
        """
        if total_orders == 0:
            return 0.0

        return float(multi_item_orders) / float(total_orders)

    def _compute_seasonality_index(self, daily_sales: List[Dict]) -> float:
        """Compute seasonality index (current vs. average).

        Feature 6: Is current period above/below seasonal average?
        """
        if not daily_sales:
            return 1.0  # No data = neutral seasonality

        # Simplified: return 1.0 (neutral)
        # In production: would compute current_month_revenue / avg_monthly_revenue
        return 1.0

    def _compute_loyalty_tier_feature(self, customer: Dict) -> float:
        """Compute loyalty tier as numeric feature.

        Feature 7: What loyalty tier is customer?
        """
        tier = customer.get("loyalty_tier", "NONE")
        return self.LOYALTY_TIER_MAPPING.get(tier, 0.0)

    def _default_features(self, customer_id: UUID) -> LTVFeatures:
        """Return default feature vector for missing customers."""
        return LTVFeatures(
            customer_id=customer_id,
            historical_ltv=0.0,
            cohort_avg_ltv=1500.0,
            cumulative_orders=0,
            product_category_spend={},
            repeat_purchase_rate=0.0,
            seasonality_index=1.0,
            loyalty_tier=0.0,
        )
