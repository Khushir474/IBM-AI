"""Dynamic pricing and discount optimization service (Task 3.4)."""

import logging
from typing import Dict, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PriceRecommendation:
    """Price recommendation for a product."""

    product_id: str
    current_price: float
    recommended_price: float
    discount_pct: float
    expected_revenue_impact: Optional[Dict] = None  # {"daily_change": -5, "units_change": 10}
    margin_impact: Optional[float] = None  # Expected margin %
    confidence: Optional[float] = None
    reason: Optional[str] = None


@dataclass
class ElasticityEstimate:
    """Price elasticity estimate for product."""

    product_id: str
    discount_pct: float
    expected_recovery_rate: float  # % of abandoned carts that convert
    confidence: float  # 0-1
    sample_size: int
    last_updated_iso: str


class PricingService:
    """Business logic for dynamic pricing, discount optimization, elasticity learning."""

    def __init__(
        self,
        feature_engineer,
        model_inference,
        explainer,
        pricing_dao=None,
        cache_manager=None,
    ):
        """Initialize PricingService.

        Args:
            feature_engineer: PricingFeatureEngineer instance
            model_inference: ModelInference instance
            explainer: Explainer instance
            pricing_dao: Optional DAO for pricing history/guardrails
            cache_manager: Optional cache manager
        """
        self.feature_engineer = feature_engineer
        self.model_inference = model_inference
        self.explainer = explainer
        self.pricing_dao = pricing_dao
        self.cache_manager = cache_manager

    def recommend_price(self, product_id: str) -> Optional[PriceRecommendation]:
        """Recommend optimal price for product based on recovery potential.

        Args:
            product_id: Product ID

        Returns:
            PriceRecommendation with price, discount, revenue impact

        REQ-017: Recommend Optimal Discounts by Product & Cohort
        """
        try:
            # Compute features
            features = self.feature_engineer.compute_features(product_id)
            if features is None:
                logger.warning(f"Could not compute pricing features for {product_id}")
                return None

            # Get recommendation from model
            recommendation = self.model_inference.recommend_price(features)

            # Get current price (from features or estimate)
            # In real implementation, would fetch from products table
            # For now, estimate based on competitor price
            current_price = 100.0  # Default estimate
            if hasattr(features, 'competitor_price_gap'):
                current_price = max(50, features.competitor_price_gap + 100)

            # Calculate discount
            recommended_price = recommendation["recommended_price"]
            discount_pct = ((current_price - recommended_price) / current_price * 100) if current_price > 0 else 0

            # Get factors
            feature_dict = self._features_to_dict(features)
            factors = self.explainer.explain_price_recommendation(
                product_id=product_id,
                recommendation=recommendation,
                features=feature_dict,
                top_n=3,
            )

            return PriceRecommendation(
                product_id=product_id,
                current_price=current_price,
                recommended_price=recommended_price,
                discount_pct=min(discount_pct, 30),  # Cap at 30%
                confidence=0.7,
                reason=f"Based on elasticity={features.price_elasticity:.2f}, inventory={features.inventory_days_supply:.0f}d",
            )

        except Exception as e:
            logger.error(f"Error recommending price for {product_id}: {e}")
            return None

    def quantify_impact(
        self,
        product_id: str,
        recommendation: PriceRecommendation,
    ) -> Dict:
        """Quantify revenue, margin, and volume impact of price recommendation.

        Args:
            product_id: Product ID
            recommendation: PriceRecommendation

        Returns:
            Dict with impact estimates {revenue_change, units_change, margin_pct}

        REQ-018: Quantify Revenue Impact of Discount Strategies
        """
        try:
            current_price = recommendation.current_price
            recommended_price = recommendation.recommended_price

            # Simplified elasticity-based impact calculation
            # In real implementation, would use learned elasticity model
            price_change_pct = (recommended_price - current_price) / current_price if current_price > 0 else 0

            # Assume elasticity of 1.5 (demand increases 1.5% per 1% price decrease)
            elasticity = 1.5
            units_change_pct = price_change_pct * elasticity * -1  # Negative sign because lower price = more units

            # Revenue impact
            revenue_change_pct = (price_change_pct + units_change_pct) / 2
            daily_revenue = current_price * 100  # Assume 100 units/day baseline
            daily_revenue_change = daily_revenue * revenue_change_pct

            # Margin impact
            current_margin = 0.35  # Assume 35% baseline
            new_margin = current_margin + (current_margin * price_change_pct)

            return {
                "revenue_change_daily": daily_revenue_change,
                "units_change_daily": units_change_pct * 100,  # 100 unit baseline
                "margin_pct": new_margin,
                "roi": "positive" if daily_revenue_change > 0 else "negative",
            }

        except Exception as e:
            logger.error(f"Error quantifying impact: {e}")
            return {}

    def apply_guardrails(
        self,
        product_id: str,
        recommendation: PriceRecommendation,
        guardrails: Dict,
    ) -> PriceRecommendation:
        """Apply business constraints (min/max discount, margin floor) to recommendation.

        Args:
            product_id: Product ID
            recommendation: PriceRecommendation
            guardrails: Dict with {min_discount, max_discount, min_margin}

        Returns:
            Modified PriceRecommendation respecting constraints

        REQ-020: Set Price & Discount Guardrails
        """
        min_discount = guardrails.get("min_discount", 0)
        max_discount = guardrails.get("max_discount", 30)
        min_margin = guardrails.get("min_margin", 0.20)

        # Clamp discount
        clamped_discount = max(min_discount, min(recommendation.discount_pct, max_discount))

        # Recalculate recommended price
        new_recommended_price = recommendation.current_price * (1 - clamped_discount / 100)

        # Check margin floor
        if recommendation.margin_impact and recommendation.margin_impact < min_margin:
            logger.warning(
                f"Recommendation for {product_id} violates margin floor ({recommendation.margin_impact} < {min_margin})"
            )
            # Adjust to respect margin
            allowed_discount = (1 - min_margin) * 100
            clamped_discount = min(clamped_discount, allowed_discount)
            new_recommended_price = recommendation.current_price * (1 - clamped_discount / 100)

        return PriceRecommendation(
            product_id=recommendation.product_id,
            current_price=recommendation.current_price,
            recommended_price=new_recommended_price,
            discount_pct=clamped_discount,
            confidence=recommendation.confidence,
            reason=f"{recommendation.reason} [guardrails applied]",
        )

    def handle_inventory_pricing(
        self,
        product_id: str,
        stock_quantity: int,
        days_supply: float,
    ) -> Dict:
        """Adjust pricing based on inventory level.

        Args:
            product_id: Product ID
            stock_quantity: Current stock
            days_supply: Days of supply remaining

        Returns:
            Dict with pricing strategy recommendation

        REQ-021: Handle Inventory-Driven Discounting
        """
        recommendation = {
            "strategy": "standard",
            "discount_pct": 0,
            "reason": "",
        }

        # Overstock: aggressive discount to move inventory
        if days_supply > 60:
            recommendation = {
                "strategy": "overstock_clearance",
                "discount_pct": 20,
                "reason": f"Overstock detected: {days_supply:.0f} days supply",
            }

        # Understock: preserve margin, no discount
        elif days_supply < 7:
            recommendation = {
                "strategy": "preserve_margin",
                "discount_pct": 0,
                "reason": f"Understock: only {days_supply:.1f} days supply remaining",
            }

        # Out of stock: recommend substitution
        elif days_supply <= 0:
            recommendation = {
                "strategy": "product_substitution",
                "discount_pct": 0,
                "reason": "Out of stock - recommend product substitution",
            }

        return recommendation

    def prevent_discount_abuse(
        self,
        product_id: str,
        customer_id: str,
        recent_discounts: List[Dict],
    ) -> Dict:
        """Check for discount abuse (customer or product level).

        Args:
            product_id: Product ID
            customer_id: Customer ID
            recent_discounts: List of recent discounts [{discount_pct, date_iso}]

        Returns:
            Dict with {approved: bool, reason: str, warning: str}

        REQ-022: Prevent Discount Abuse & Margin Erosion
        """
        result = {
            "approved": True,
            "reason": "No abuse detected",
            "warning": None,
        }

        # Check per-customer discount frequency
        if len(recent_discounts) >= 3:
            result["warning"] = f"Customer has received {len(recent_discounts)} discounts in 30d (consider cap)"

        # Check per-product discount rate
        avg_discount = sum(d.get("discount_pct", 0) for d in recent_discounts) / len(
            recent_discounts
        ) if recent_discounts else 0

        if avg_discount > 40:
            result["approved"] = False
            result["reason"] = f"Product avg discount {avg_discount:.1f}% exceeds 40% threshold"
            result["warning"] = "Consider delisting or raising baseline price"

        return result

    @staticmethod
    def _features_to_dict(features) -> Dict:
        """Convert PricingFeatures object to dict for explainer.

        Args:
            features: PricingFeatures object

        Returns:
            Dict with feature names and values
        """
        return {
            "inventory_days_supply": features.inventory_days_supply,
            "price_elasticity": features.price_elasticity,
            "competitor_price_gap": features.competitor_price_gap,
            "product_margin_pct": features.product_margin_pct,
            "weekly_units_sold": features.weekly_units_sold,
            "weekly_return_rate": features.weekly_return_rate,
        }
