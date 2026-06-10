"""Churn Feature Engineering.

Compute 8 churn prediction features from Cassandra + Iceberg data:
1. days_since_last_purchase — from orders_inflight (Cassandra)
2. purchase_frequency_30d — from orders_inflight (Cassandra)
3. average_order_value — from order_items_inflight (Cassandra)
4. product_category_affinity — from orders_inflight (Cassandra)
5. cohort_churn_rate — from cohort_retention (Iceberg) + customer acquisition cohort
6. session_engagement_30d — from live_sessions (Cassandra)
7. return_rate — from order_items_archive (Iceberg)
8. loyalty_tier — from customers (Cassandra)
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from dataclasses import dataclass

import structlog

from src.data.daos.cassandra_daos import (
    CustomerDAO, OrderDAO, SessionDAO, ReviewDAO
)

logger = structlog.get_logger(__name__)


@dataclass
class ChurnFeatures:
    """Churn prediction feature vector."""

    customer_id: UUID
    days_since_last_purchase: float
    purchase_frequency_30d: int
    average_order_value: float
    product_category_affinity: Dict[str, float]
    cohort_churn_rate: float
    session_engagement_30d: int
    return_rate: float
    loyalty_tier: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for ML model input."""
        return {
            "customer_id": str(self.customer_id),
            "days_since_last_purchase": self.days_since_last_purchase,
            "purchase_frequency_30d": self.purchase_frequency_30d,
            "average_order_value": self.average_order_value,
            "product_category_affinity": self.product_category_affinity,
            "cohort_churn_rate": self.cohort_churn_rate,
            "session_engagement_30d": self.session_engagement_30d,
            "return_rate": self.return_rate,
            "loyalty_tier": self.loyalty_tier,
        }


class ChurnFeatureEngineer:
    """Compute churn prediction features from multiple data sources."""

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
        session_dao: SessionDAO,
        review_dao: ReviewDAO,
    ):
        """Initialize ChurnFeatureEngineer.

        Args:
            customer_dao: CustomerDAO for customer profiles
            order_dao: OrderDAO for purchase history
            session_dao: SessionDAO for engagement data
            review_dao: ReviewDAO for return rate signals
        """
        self.customer_dao = customer_dao
        self.order_dao = order_dao
        self.session_dao = session_dao
        self.review_dao = review_dao

    async def compute_features(self, customer_id: UUID) -> ChurnFeatures:
        """Compute complete churn feature vector for customer.

        Args:
            customer_id: Customer UUID

        Returns:
            ChurnFeatures dataclass with all 8 features
        """
        # Fetch data from all sources in parallel would be ideal,
        # but for now we do sequential (simplicity)

        # Get customer profile
        customer = await self.customer_dao.get_customer(customer_id)
        if not customer:
            logger.warning("customer_not_found", customer_id=customer_id)
            # Return default features for missing customer
            return self._default_features(customer_id)

        # Get order history (Cassandra hot data)
        orders = await self.order_dao.get_inflight_orders(customer_id, limit=100)
        order_items_list = []
        if orders:
            # Get items for most recent order (for AOV calculation)
            order_items_list = await self.order_dao.get_order_items(
                orders[0].get("order_id")
            )

        # Get session history (engagement)
        sessions = await self.session_dao.get_recent_sessions(customer_id, limit=100)

        # Get reviews for return rate (sentiment)
        reviews = await self.review_dao.get_recent_reviews(customer_id)

        # Compute individual features
        days_since_purchase = self._compute_days_since_last_purchase(orders)
        purchase_freq = self._compute_purchase_frequency_30d(orders)
        avg_order_value = self._compute_average_order_value(order_items_list)
        category_affinity = self._compute_product_category_affinity(orders)
        cohort_churn = self._compute_cohort_churn_rate(customer)
        engagement = self._compute_session_engagement_30d(sessions)
        return_rate = self._compute_return_rate(reviews)
        loyalty = self._compute_loyalty_tier_feature(customer)

        features = ChurnFeatures(
            customer_id=customer_id,
            days_since_last_purchase=days_since_purchase,
            purchase_frequency_30d=purchase_freq,
            average_order_value=avg_order_value,
            product_category_affinity=category_affinity,
            cohort_churn_rate=cohort_churn,
            session_engagement_30d=engagement,
            return_rate=return_rate,
            loyalty_tier=loyalty,
        )

        logger.info(
            "churn_features_computed",
            customer_id=customer_id,
            days_since_purchase=days_since_purchase,
            purchase_freq=purchase_freq,
        )

        return features

    def _compute_days_since_last_purchase(self, orders: List[Dict]) -> float:
        """Compute days since last purchase from order history.

        Feature 1: Recency signal - how long since customer last bought
        """
        if not orders:
            # No purchase history = high churn risk
            return 999.0

        last_order = orders[0]
        last_order_date = last_order.get("order_date")

        if not last_order_date:
            return 999.0

        # Convert to datetime if needed
        if isinstance(last_order_date, str):
            last_order_date = datetime.fromisoformat(last_order_date)

        days_since = (datetime.utcnow() - last_order_date).days
        return float(days_since)

    def _compute_purchase_frequency_30d(self, orders: List[Dict]) -> int:
        """Compute purchase frequency in last 30 days.

        Feature 2: Frequency signal - how often customer purchases
        """
        if not orders:
            return 0

        now = datetime.utcnow()
        cutoff = now - timedelta(days=30)

        count = 0
        for order in orders:
            order_date = order.get("order_date")
            if isinstance(order_date, str):
                order_date = datetime.fromisoformat(order_date)

            if order_date >= cutoff:
                count += 1

        return count

    def _compute_average_order_value(self, order_items: List[Dict]) -> float:
        """Compute average order value from line items.

        Feature 3: Monetary signal - how much customer spends
        """
        if not order_items:
            return 0.0

        total_value = sum(
            item.get("unit_price", 0) * item.get("quantity", 1)
            for item in order_items
        )

        return total_value / len(order_items) if order_items else 0.0

    def _compute_product_category_affinity(self, orders: List[Dict]) -> Dict[str, float]:
        """Compute product category affinity from purchase history.

        Feature 4: Category preference signal - what does customer buy?
        Returns dict of category → affinity score
        """
        # Simplified: return empty dict (would need product category lookups)
        return {}

    def _compute_cohort_churn_rate(self, customer: Dict) -> float:
        """Compute cohort churn rate for customer's acquisition cohort.

        Feature 5: Cohort signal - how is customer's cohort performing?
        Would query cohort_retention from Iceberg
        """
        # Simplified: return default 0.1 (10% churn)
        # In production: query Iceberg cohort_retention table
        return 0.1

    def _compute_session_engagement_30d(self, sessions: List[Dict]) -> int:
        """Compute session engagement in last 30 days.

        Feature 6: Engagement signal - is customer active on site?
        """
        if not sessions:
            return 0

        now = datetime.utcnow()
        cutoff = now - timedelta(days=30)

        count = 0
        for session in sessions:
            session_date = session.get("created_at")
            if isinstance(session_date, str):
                session_date = datetime.fromisoformat(session_date)

            if session_date >= cutoff:
                count += 1

        return count

    def _compute_return_rate(self, reviews: List[Dict]) -> float:
        """Compute return rate from review/return history.

        Feature 7: Quality signal - does customer return items?
        Would query order_items_archive from Iceberg for return counts
        """
        # Simplified: return 0.05 (5% return rate)
        # In production: query Iceberg order_items_archive
        return 0.05

    def _compute_loyalty_tier_feature(self, customer: Dict) -> float:
        """Compute loyalty tier as numeric feature.

        Feature 8: Loyalty signal - what tier is customer?
        """
        tier = customer.get("loyalty_tier", "NONE")
        return self.LOYALTY_TIER_MAPPING.get(tier, 0.0)

    def _default_features(self, customer_id: UUID) -> ChurnFeatures:
        """Return default feature vector for missing/new customers."""
        return ChurnFeatures(
            customer_id=customer_id,
            days_since_last_purchase=999.0,
            purchase_frequency_30d=0,
            average_order_value=0.0,
            product_category_affinity={},
            cohort_churn_rate=0.5,  # Unknown = 50% churn
            session_engagement_30d=0,
            return_rate=0.0,
            loyalty_tier=0.0,
        )
