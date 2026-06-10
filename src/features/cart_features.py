"""Cart Abandonment Feature Engineering.

Compute 8 cart abandonment recovery features from Cassandra + Iceberg data:
1. cart_value — sum of items in active_carts (Cassandra)
2. cart_item_count — count items in active_carts (Cassandra)
3. item_avg_recovery_rate — from product_performance_weekly (Iceberg)
4. customer_repeat_buyer — customers.total_orders > 1 (Cassandra)
5. time_since_abandon — NOW() - active_carts.added_at (Cassandra)
6. previous_abandon_count — from custom tracking table (Cassandra)
7. shipping_cost_ratio — estimated from order history / cart value
8. device_type — from live_sessions (Cassandra)
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from dataclasses import dataclass

import structlog

from src.data.daos.cassandra_daos import CustomerDAO, CartDAO, SessionDAO
from src.data.daos.iceberg_daos import ProductPerformanceDAO

logger = structlog.get_logger(__name__)


@dataclass
class CartAbandonmentFeatures:
    """Cart abandonment recovery feature vector."""

    customer_id: UUID
    product_id: UUID
    cart_value: float
    cart_item_count: int
    item_avg_recovery_rate: float
    customer_repeat_buyer: bool
    time_since_abandon: float
    previous_abandon_count: int
    shipping_cost_ratio: float
    device_type: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for ML model input."""
        return {
            "customer_id": str(self.customer_id),
            "product_id": str(self.product_id),
            "cart_value": self.cart_value,
            "cart_item_count": self.cart_item_count,
            "item_avg_recovery_rate": self.item_avg_recovery_rate,
            "customer_repeat_buyer": self.customer_repeat_buyer,
            "time_since_abandon": self.time_since_abandon,
            "previous_abandon_count": self.previous_abandon_count,
            "shipping_cost_ratio": self.shipping_cost_ratio,
            "device_type": self.device_type,
        }


class CartAbandonmentFeatureEngineer:
    """Compute cart abandonment recovery features from multiple data sources."""

    def __init__(
        self,
        customer_dao: CustomerDAO,
        cart_dao: CartDAO,
        session_dao: SessionDAO,
        product_perf_dao: ProductPerformanceDAO,
    ):
        """Initialize CartAbandonmentFeatureEngineer.

        Args:
            customer_dao: CustomerDAO for customer profiles
            cart_dao: CartDAO for cart data
            session_dao: SessionDAO for device type
            product_perf_dao: ProductPerformanceDAO for recovery rates
        """
        self.customer_dao = customer_dao
        self.cart_dao = cart_dao
        self.session_dao = session_dao
        self.product_perf_dao = product_perf_dao

    async def compute_features(
        self, customer_id: UUID, product_id: UUID
    ) -> CartAbandonmentFeatures:
        """Compute complete cart abandonment feature vector.

        Args:
            customer_id: Customer UUID
            product_id: Product UUID in abandoned cart

        Returns:
            CartAbandonmentFeatures dataclass with all 8 features
        """
        # Get customer profile
        customer = await self.customer_dao.get_customer(customer_id)
        if not customer:
            logger.warning("customer_not_found", customer_id=customer_id)
            return self._default_features(customer_id, product_id)

        # Get active carts for customer
        carts = await self.cart_dao.get_active_carts(customer_id)

        # Get recent sessions for device type
        sessions = await self.session_dao.get_recent_sessions(customer_id, limit=5)

        # Get product performance for recovery rate
        product_perf = await self.product_perf_dao.get_weekly_performance(
            str(product_id), weeks=4
        )

        # Compute individual features
        cart_value = self._compute_cart_value(carts)
        cart_count = self._compute_cart_item_count(carts)
        recovery_rate = self._compute_item_avg_recovery_rate(product_perf)
        is_repeat = self._compute_customer_repeat_buyer(customer.get("total_orders", 0))
        time_abandon = self._compute_time_since_abandon(carts)
        prev_abandons = self._compute_previous_abandon_count(customer)
        shipping_ratio = self._compute_shipping_cost_ratio(cart_value)
        device = self._compute_device_type(sessions)

        features = CartAbandonmentFeatures(
            customer_id=customer_id,
            product_id=product_id,
            cart_value=cart_value,
            cart_item_count=cart_count,
            item_avg_recovery_rate=recovery_rate,
            customer_repeat_buyer=is_repeat,
            time_since_abandon=time_abandon,
            previous_abandon_count=prev_abandons,
            shipping_cost_ratio=shipping_ratio,
            device_type=device,
        )

        logger.info(
            "cart_abandonment_features_computed",
            customer_id=customer_id,
            product_id=product_id,
            cart_value=cart_value,
            time_since_abandon=time_abandon,
        )

        return features

    def _compute_cart_value(self, cart_items: List[Dict]) -> float:
        """Compute total cart value.

        Feature 1: What is the total value of abandoned items?
        """
        if not cart_items:
            return 0.0

        total = sum(
            item.get("unit_price", 0) * item.get("quantity", 1)
            for item in cart_items
        )
        return float(total)

    def _compute_cart_item_count(self, cart_items: List[Dict]) -> int:
        """Compute total number of items in cart.

        Feature 2: How many items are in the abandoned cart?
        """
        if not cart_items:
            return 0

        return sum(item.get("quantity", 0) for item in cart_items)

    def _compute_item_avg_recovery_rate(self, product_perf: List[Dict]) -> float:
        """Compute average recovery rate for items in cart.

        Feature 3: How recoverable are items in this cart (based on product history)?
        """
        if not product_perf:
            return 0.5  # Default: 50% recovery rate if unknown

        # Simplified: average the return rates (inverse of recovery)
        # In production: would sum units_sold weighted by return_rate
        recovery_rates = [1.0 - item.get("return_rate", 0.1) for item in product_perf]
        return sum(recovery_rates) / len(recovery_rates) if recovery_rates else 0.5

    def _compute_customer_repeat_buyer(self, total_orders: int) -> bool:
        """Check if customer is a repeat buyer.

        Feature 4: Is this a repeat customer (more likely to convert)?
        """
        return total_orders > 1

    def _compute_time_since_abandon(self, cart_items: List[Dict]) -> float:
        """Compute hours since cart was abandoned.

        Feature 5: How long has the cart been abandoned?
        """
        if not cart_items:
            return 0.0

        now = datetime.utcnow()
        earliest_abandon = min(
            (item.get("added_at") for item in cart_items if item.get("added_at")),
            default=now,
        )

        if isinstance(earliest_abandon, str):
            earliest_abandon = datetime.fromisoformat(earliest_abandon)

        hours_since = (now - earliest_abandon).total_seconds() / 3600.0
        return float(hours_since)

    def _compute_previous_abandon_count(self, customer: Dict) -> int:
        """Compute count of previous cart abandonments.

        Feature 6: How many times has this customer abandoned carts before?
        In production: would query custom abandonment tracking table
        """
        # Simplified: return 0 (would track in custom table)
        return customer.get("previous_abandon_count", 0)

    def _compute_shipping_cost_ratio(self, cart_value: float) -> float:
        """Compute shipping cost as ratio of cart value.

        Feature 7: How expensive is shipping relative to cart value?
        Estimated at 10% or 5% depending on cart size
        """
        if cart_value == 0:
            return 0.0

        # Estimate: 10% for small carts, 5% for larger carts
        estimated_shipping = 20.0 if cart_value < 100 else 10.0
        return estimated_shipping / cart_value

    def _compute_device_type(self, sessions: List[Dict]) -> str:
        """Get device type from recent session.

        Feature 8: What device is customer using (desktop/mobile/tablet)?
        """
        if not sessions:
            return "unknown"

        recent = sessions[0]
        return recent.get("device_type", "unknown")

    def _default_features(
        self, customer_id: UUID, product_id: UUID
    ) -> CartAbandonmentFeatures:
        """Return default feature vector for missing data."""
        return CartAbandonmentFeatures(
            customer_id=customer_id,
            product_id=product_id,
            cart_value=0.0,
            cart_item_count=0,
            item_avg_recovery_rate=0.5,
            customer_repeat_buyer=False,
            time_since_abandon=0.0,
            previous_abandon_count=0,
            shipping_cost_ratio=0.1,
            device_type="unknown",
        )
