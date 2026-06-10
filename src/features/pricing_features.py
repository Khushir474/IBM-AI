"""Dynamic Pricing Feature Engineering.

Compute 6 pricing optimization features from Cassandra + Iceberg data:
1. inventory_days_supply — products.stock_quantity / avg daily sales (Cassandra + Iceberg)
2. price_elasticity — from learned elasticity table or default (Cassandra)
3. competitor_price_gap — our_price - competitor_price (Iceberg)
4. product_margin_pct — (price - cost) / price (Cassandra)
5. weekly_units_sold — from product_performance_weekly (Iceberg)
6. weekly_return_rate — from product_performance_weekly (Iceberg)
"""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import date, datetime, timedelta
from dataclasses import dataclass

import structlog

from src.data.daos.cassandra_daos import ProductDAO
from src.data.daos.iceberg_daos import (
    DailySalesSummaryDAO,
    ProductPerformanceDAO,
    CompetitorPricesDAO,
)

logger = structlog.get_logger(__name__)


@dataclass
class PricingFeatures:
    """Pricing optimization feature vector."""

    product_id: UUID
    inventory_days_supply: float
    price_elasticity: float
    competitor_price_gap: float
    product_margin_pct: float
    weekly_units_sold: int
    weekly_return_rate: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for ML model input."""
        return {
            "product_id": str(self.product_id),
            "inventory_days_supply": self.inventory_days_supply,
            "price_elasticity": self.price_elasticity,
            "competitor_price_gap": self.competitor_price_gap,
            "product_margin_pct": self.product_margin_pct,
            "weekly_units_sold": self.weekly_units_sold,
            "weekly_return_rate": self.weekly_return_rate,
        }


class PricingFeatureEngineer:
    """Compute dynamic pricing optimization features from multiple data sources."""

    DEFAULT_ELASTICITY = -1.2  # Default price elasticity

    def __init__(
        self,
        product_dao: ProductDAO,
        daily_sales_dao: DailySalesSummaryDAO,
        product_perf_dao: ProductPerformanceDAO,
        competitor_dao: CompetitorPricesDAO,
    ):
        """Initialize PricingFeatureEngineer.

        Args:
            product_dao: ProductDAO for product profiles
            daily_sales_dao: DailySalesSummaryDAO for demand
            product_perf_dao: ProductPerformanceDAO for velocity/quality
            competitor_dao: CompetitorPricesDAO for market context
        """
        self.product_dao = product_dao
        self.daily_sales_dao = daily_sales_dao
        self.product_perf_dao = product_perf_dao
        self.competitor_dao = competitor_dao

    async def compute_features(self, product_id: UUID) -> PricingFeatures:
        """Compute complete pricing feature vector for product.

        Args:
            product_id: Product UUID

        Returns:
            PricingFeatures dataclass with all 6 features
        """
        # Get product profile (Cassandra)
        product = await self.product_dao.get_product(product_id)
        if not product:
            logger.warning("product_not_found", product_id=product_id)
            return self._default_features(product_id)

        # Get daily sales history (Iceberg)
        date_range = (
            (datetime.utcnow() - timedelta(days=90)).date(),
            datetime.utcnow().date(),
        )
        daily_sales = await self.daily_sales_dao.get_daily_revenue(date_range)

        # Get product performance metrics (Iceberg)
        product_perf = await self.product_perf_dao.get_weekly_performance(
            str(product_id), weeks=12
        )

        # Get competitor prices (Iceberg)
        competitor_prices = await self.competitor_dao.get_latest_competitor_prices()

        # Compute individual features
        inventory_days = self._compute_inventory_days_supply(
            product.get("stock_quantity", 0),
            self._compute_avg_daily_sales(daily_sales),
        )
        elasticity = self._compute_price_elasticity(product.get("elasticity"))
        price_gap = self._compute_competitor_price_gap(
            product.get("price", 0),
            self._get_avg_competitor_price(competitor_prices),
        )
        margin = self._compute_product_margin_pct(
            product.get("price", 0), product.get("cost", 0)
        )
        weekly_units = self._compute_weekly_units_sold(product_perf)
        return_rate = self._compute_weekly_return_rate(product_perf)

        features = PricingFeatures(
            product_id=product_id,
            inventory_days_supply=inventory_days,
            price_elasticity=elasticity,
            competitor_price_gap=price_gap,
            product_margin_pct=margin,
            weekly_units_sold=weekly_units,
            weekly_return_rate=return_rate,
        )

        logger.info(
            "pricing_features_computed",
            product_id=product_id,
            inventory_days=inventory_days,
            competitor_gap=price_gap,
            margin_pct=margin,
        )

        return features

    def _compute_inventory_days_supply(
        self, stock_quantity: float, avg_daily_sales: float
    ) -> float:
        """Compute inventory days of supply.

        Feature 1: How long until inventory runs out at current sales velocity?
        """
        if avg_daily_sales == 0:
            return 0.0

        return stock_quantity / avg_daily_sales

    def _compute_avg_daily_sales(self, daily_sales: List[Dict]) -> float:
        """Compute average daily sales units from sales history."""
        if not daily_sales:
            return 0.0

        total_units = sum(item.get("units_sold", 0) for item in daily_sales)
        return total_units / len(daily_sales) if daily_sales else 0.0

    def _compute_price_elasticity(self, elasticity: Optional[float]) -> float:
        """Compute price elasticity.

        Feature 2: How sensitive is demand to price changes?
        """
        if elasticity is not None:
            return float(elasticity)

        # Default elasticity if not learned yet
        return self.DEFAULT_ELASTICITY

    def _compute_competitor_price_gap(
        self, our_price: float, competitor_price: float
    ) -> float:
        """Compute price gap versus competitors.

        Feature 3: Are we above or below market?
        Positive = we're more expensive, negative = we're cheaper
        """
        if competitor_price == 0:
            return 0.0

        return our_price - competitor_price

    def _get_avg_competitor_price(self, competitor_prices: List[Dict]) -> float:
        """Get average competitor price."""
        if not competitor_prices:
            return 0.0

        prices = [p.get("competitor_price", 0) for p in competitor_prices]
        return sum(prices) / len(prices) if prices else 0.0

    def _compute_product_margin_pct(self, price: float, cost: float) -> float:
        """Compute product margin percentage.

        Feature 4: What's our profit margin on this product?
        """
        if price == 0:
            return 0.0

        return (price - cost) / price

    def _compute_weekly_units_sold(self, product_perf: List[Dict]) -> int:
        """Compute average weekly units sold.

        Feature 5: What's the weekly velocity/demand?
        """
        if not product_perf:
            return 0

        total_units = sum(item.get("units_sold", 0) for item in product_perf)
        return int(total_units / len(product_perf)) if product_perf else 0

    def _compute_weekly_return_rate(self, product_perf: List[Dict]) -> float:
        """Compute average weekly return rate.

        Feature 6: What's the product quality/satisfaction rate?
        """
        if not product_perf:
            return 0.0

        total_rate = sum(item.get("return_rate", 0) for item in product_perf)
        return total_rate / len(product_perf) if product_perf else 0.0

    def _default_features(self, product_id: UUID) -> PricingFeatures:
        """Return default feature vector for missing products."""
        return PricingFeatures(
            product_id=product_id,
            inventory_days_supply=0.0,
            price_elasticity=self.DEFAULT_ELASTICITY,
            competitor_price_gap=0.0,
            product_margin_pct=0.0,
            weekly_units_sold=0,
            weekly_return_rate=0.0,
        )
