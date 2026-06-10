"""Cart abandonment and recovery service (Task 3.3)."""

import logging
from typing import List, Dict, Optional
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class RecoveryTier(str, Enum):
    """Cart recovery probability tier."""

    LOW = "LOW"  # 0-29
    MEDIUM = "MEDIUM"  # 30-59
    HIGH = "HIGH"  # 60-100


@dataclass
class AbandonedCart:
    """Abandoned cart with recovery score and recommendation."""

    customer_id: str
    product_id: str
    cart_value: float
    item_count: int
    abandon_time_iso: str
    recovery_score: float  # 0-100
    recovery_tier: RecoveryTier
    factors: List[Dict] = None
    recommended_offer: Optional[Dict] = None


@dataclass
class RecoveryOfferRecommendation:
    """Recommended recovery offer for abandoned cart."""

    offer_type: str  # "discount", "free_shipping", "product_substitution", "bundle"
    discount_pct: Optional[float] = None
    free_shipping: bool = False
    conversion_probability: Optional[float] = None


@dataclass
class RepeatAbandoner:
    """Customer with repeated cart abandonments."""

    customer_id: str
    abandon_count_30d: int
    total_abandoned_value_30d: float
    avg_recovery_rate: float
    risk_level: str  # "low", "medium", "high"


class CartService:
    """Business logic for cart abandonment detection, recovery scoring, recommendations."""

    def __init__(
        self,
        feature_engineer,
        model_inference,
        explainer,
        cart_dao=None,
        cache_manager=None,
    ):
        """Initialize CartService.

        Args:
            feature_engineer: CartAbandonmentFeatureEngineer instance
            model_inference: ModelInference instance
            explainer: Explainer instance
            cart_dao: Optional CartDAO for Cassandra queries
            cache_manager: Optional cache manager
        """
        self.feature_engineer = feature_engineer
        self.model_inference = model_inference
        self.explainer = explainer
        self.cart_dao = cart_dao
        self.cache_manager = cache_manager

    def detect_abandoned_carts(
        self,
        idle_minutes: int = 60,
        recovery_tier: Optional[RecoveryTier] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AbandonedCart]:
        """Detect abandoned carts and score by recovery potential.

        Args:
            idle_minutes: Idle threshold for abandonment (default 60 min)
            recovery_tier: Filter by recovery tier (HIGH/MEDIUM/LOW) or None for all
            limit: Number of results
            offset: Pagination offset

        Returns:
            List of AbandonedCart with recovery scores

        REQ-010: Detect Abandoned Carts in Real-Time
        REQ-011: Score Carts by Recovery Likelihood
        """
        if not self.cart_dao:
            logger.warning("CartDAO not available, returning empty list")
            return []

        try:
            # Get abandoned carts from Cassandra
            carts = self.cart_dao.detect_abandoned_carts(
                idle_minutes=idle_minutes,
                limit=limit + offset,
            )

            if not carts:
                return []

            # Score each cart
            scored = []
            for cart in carts[offset : offset + limit]:
                try:
                    score = self.score_recovery(
                        customer_id=cart["customer_id"],
                        product_id=cart["product_id"],
                    )

                    tier = self._score_to_tier(score)

                    # Filter by tier if specified
                    if recovery_tier and tier != recovery_tier:
                        continue

                    # Get factors
                    features = self.feature_engineer.compute_features(
                        customer_id=cart["customer_id"],
                        product_id=cart["product_id"],
                    )
                    feature_dict = self._features_to_dict(features) if features else {}
                    factors = self.explainer.explain_cart_abandonment(
                        customer_id=cart["customer_id"],
                        product_id=cart["product_id"],
                        score=score,
                        features=feature_dict,
                        top_n=3,
                    )
                    factors_list = [
                        {
                            "name": f.feature_name,
                            "description": f.description,
                            "contribution": f.contribution_score,
                        }
                        for f in factors
                    ]

                    # Get recommendation
                    offer = self.recommend_recovery_offer(
                        customer_id=cart["customer_id"],
                        product_id=cart["product_id"],
                    )

                    abandoned = AbandonedCart(
                        customer_id=cart["customer_id"],
                        product_id=cart["product_id"],
                        cart_value=cart.get("cart_value", 0.0),
                        item_count=cart.get("item_count", 0),
                        abandon_time_iso=cart.get("abandon_time", ""),
                        recovery_score=score,
                        recovery_tier=tier,
                        factors=factors_list,
                        recommended_offer={
                            "type": offer.offer_type,
                            "discount_pct": offer.discount_pct,
                            "free_shipping": offer.free_shipping,
                            "conversion_prob": offer.conversion_probability,
                        },
                    )
                    scored.append(abandoned)

                except Exception as e:
                    logger.error(f"Error scoring cart {cart.get('product_id')}: {e}")
                    continue

            return scored

        except Exception as e:
            logger.error(f"Error detecting abandoned carts: {e}")
            return []

    def score_recovery(self, customer_id: str, product_id: str) -> float:
        """Score cart recovery probability (0-100).

        Args:
            customer_id: Customer ID
            product_id: Product ID (in cart)

        Returns:
            Recovery probability score (0-100)

        REQ-011: Score Carts by Recovery Likelihood
        """
        try:
            features = self.feature_engineer.compute_features(
                customer_id=customer_id,
                product_id=product_id,
            )
            if features is None:
                return 50.0

            score = self.model_inference.predict_recovery_probability(features)
            return score

        except Exception as e:
            logger.error(f"Error scoring recovery for {customer_id}/{product_id}: {e}")
            return 50.0

    def recommend_recovery_offer(
        self,
        customer_id: str,
        product_id: str,
    ) -> RecoveryOfferRecommendation:
        """Recommend recovery offer for abandoned cart.

        Args:
            customer_id: Customer ID
            product_id: Product ID

        Returns:
            RecoveryOfferRecommendation

        REQ-013: Recommend Targeted Recovery Offers
        """
        try:
            features = self.feature_engineer.compute_features(
                customer_id=customer_id,
                product_id=product_id,
            )
            if features is None:
                return RecoveryOfferRecommendation(offer_type="discount", discount_pct=10.0)

            # Decision tree based on abandonment factors
            shipping_ratio = features.shipping_cost_ratio
            customer_repeat = features.customer_repeat_buyer
            cart_value = features.cart_value

            # High shipping cost relative to cart: offer free shipping
            if shipping_ratio > 0.20:
                return RecoveryOfferRecommendation(
                    offer_type="free_shipping",
                    free_shipping=True,
                    conversion_probability=0.22,
                )

            # High-value cart: offer smaller discount (preserve margin)
            if cart_value > 200:
                return RecoveryOfferRecommendation(
                    offer_type="discount",
                    discount_pct=10.0,
                    conversion_probability=0.18,
                )

            # New customer: offer bundle or larger discount
            if customer_repeat < 1:
                return RecoveryOfferRecommendation(
                    offer_type="bundle",
                    discount_pct=15.0,
                    conversion_probability=0.25,
                )

            # Default: moderate discount
            return RecoveryOfferRecommendation(
                offer_type="discount",
                discount_pct=12.0,
                conversion_probability=0.20,
            )

        except Exception as e:
            logger.error(f"Error recommending offer: {e}")
            return RecoveryOfferRecommendation(offer_type="discount", discount_pct=10.0)

    def flag_repeat_abandoners(self, threshold: int = 3) -> List[RepeatAbandoner]:
        """Flag customers with repeated cart abandonments.

        Args:
            threshold: Number of abandonments to trigger flag

        Returns:
            List of RepeatAbandoner

        REQ-016: Track Lost Carts & Churn Risk
        """
        # This would query Cassandra custom tracking table
        # For now, return empty list (to be integrated with DAOs)
        logger.info(f"Searching for repeat abandoners with {threshold}+ abandons in 30d")
        return []

    def _score_to_tier(self, score: float) -> RecoveryTier:
        """Convert score to recovery tier.

        Args:
            score: Recovery score (0-100)

        Returns:
            RecoveryTier

        REQ-014: Segment Abandoned Carts by Recovery Potential
        """
        if score < 30:
            return RecoveryTier.LOW
        elif score < 60:
            return RecoveryTier.MEDIUM
        else:
            return RecoveryTier.HIGH

    @staticmethod
    def _features_to_dict(features) -> Dict:
        """Convert CartFeatures object to dict for explainer.

        Args:
            features: CartFeatures object

        Returns:
            Dict with feature names and values
        """
        return {
            "cart_value": features.cart_value,
            "cart_item_count": features.cart_item_count,
            "item_avg_recovery_rate": features.item_avg_recovery_rate,
            "customer_repeat_buyer": features.customer_repeat_buyer,
            "time_since_abandon": features.time_since_abandon,
            "previous_abandon_count": features.previous_abandon_count,
            "shipping_cost_ratio": features.shipping_cost_ratio,
        }
