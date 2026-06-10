"""Churn prediction service (Task 3.1)."""

import logging
from typing import List, Dict, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from uuid import UUID

logger = logging.getLogger(__name__)


class ChurnTier(str, Enum):
    """Churn risk tier."""

    LOW = "LOW"  # 0-33
    MEDIUM = "MEDIUM"  # 34-66
    HIGH = "HIGH"  # 67-100


@dataclass
class ChurnRiskScore:
    """Churn risk score for a customer."""

    customer_id: str
    score: float  # 0-100
    tier: ChurnTier
    factors: List[Dict] = None  # List of {name, description, contribution}
    recommended_intervention: Optional[str] = None
    confidence: Optional[float] = None  # 0-1


@dataclass
class ChurnIntervention:
    """Recommended intervention for at-risk customer."""

    intervention_type: str  # "email_offer", "vip_upgrade", "product_recommendation", "phone_call"
    description: str
    recommended_discount: Optional[float] = None  # % discount
    confidence: Optional[float] = None


class ChurnService:
    """Business logic for churn prediction, scoring, and intervention."""

    def __init__(
        self,
        feature_engineer,
        model_inference,
        explainer,
        cache_manager=None,
    ):
        """Initialize ChurnService.

        Args:
            feature_engineer: ChurnFeatureEngineer instance
            model_inference: ModelInference instance
            explainer: Explainer instance
            cache_manager: Optional cache manager for scores
        """
        self.feature_engineer = feature_engineer
        self.model_inference = model_inference
        self.explainer = explainer
        self.cache_manager = cache_manager

    def score_customer(self, customer_id: str) -> ChurnRiskScore:
        """Score single customer for churn risk.

        Args:
            customer_id: Customer ID

        Returns:
            ChurnRiskScore with score, tier, factors, intervention

        REQ-001: Score Customers by Churn Risk
        """
        try:
            # Compute features
            features = self.feature_engineer.compute_features(customer_id)
            if features is None:
                logger.warning(f"Could not compute churn features for {customer_id}")
                # Return neutral score for missing data
                return ChurnRiskScore(
                    customer_id=customer_id,
                    score=50.0,
                    tier=ChurnTier.MEDIUM,
                    factors=[],
                    recommended_intervention="collect_more_data",
                )

            # Get prediction
            score = self.model_inference.predict_churn_score(features)

            # Determine tier
            tier = self._score_to_tier(score)

            # Get factors
            feature_dict = self._features_to_dict(features)
            factors = self.explainer.explain_churn_score(
                customer_id=customer_id,
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

            # Get recommended intervention
            intervention = self._compute_intervention(score, tier, feature_dict)

            return ChurnRiskScore(
                customer_id=customer_id,
                score=score,
                tier=tier,
                factors=factors_list,
                recommended_intervention=intervention.intervention_type if intervention else None,
            )

        except Exception as e:
            logger.error(f"Error scoring customer {customer_id}: {e}")
            return ChurnRiskScore(
                customer_id=customer_id,
                score=50.0,
                tier=ChurnTier.MEDIUM,
                factors=[],
                recommended_intervention="error",
            )

    def score_customers_batch(self, customer_ids: List[str]) -> List[ChurnRiskScore]:
        """Score multiple customers efficiently (batch).

        Args:
            customer_ids: List of customer IDs

        Returns:
            List of ChurnRiskScore objects

        REQ-001, REQ-003: Batch scoring for list view
        """
        if not customer_ids:
            return []

        scores = []
        for customer_id in customer_ids:
            score = self.score_customer(customer_id)
            scores.append(score)

        return scores

    def list_by_tier(
        self,
        tier: ChurnTier,
        limit: int = 100,
        offset: int = 0,
        pre_computed: Optional[Dict] = None,
    ) -> Tuple[List[ChurnRiskScore], int]:
        """List customers by churn risk tier (paginated).

        Args:
            tier: ChurnTier to filter by
            limit: Number of results to return
            offset: Pagination offset
            pre_computed: Optional pre-computed scores dict {customer_id: score}

        Returns:
            Tuple of (list of ChurnRiskScore, total_count)

        REQ-003: Segment Customers by Churn Risk Tier
        """
        if pre_computed is None:
            pre_computed = {}

        # Filter by tier
        filtered = []
        for customer_id, score in pre_computed.items():
            if self._score_to_tier(score) == tier:
                filtered.append((customer_id, score))

        # Sort by score descending (highest risk first)
        filtered.sort(key=lambda x: x[1], reverse=True)

        # Paginate
        paginated = filtered[offset : offset + limit]

        # Convert to ChurnRiskScore objects
        result = []
        for customer_id, score in paginated:
            try:
                full_score = self.score_customer(customer_id)
                result.append(full_score)
            except Exception as e:
                logger.error(f"Error converting to ChurnRiskScore: {e}")

        return result, len(filtered)

    def get_tier_summary(self, pre_computed: Optional[Dict] = None) -> Dict[str, int]:
        """Get count of customers by tier.

        Args:
            pre_computed: Optional pre-computed scores dict

        Returns:
            Dict with tier counts: {LOW: count, MEDIUM: count, HIGH: count}

        REQ-003: Segment Customers by Churn Risk Tier
        """
        if pre_computed is None:
            pre_computed = {}

        summary = {ChurnTier.LOW: 0, ChurnTier.MEDIUM: 0, ChurnTier.HIGH: 0}

        for score in pre_computed.values():
            tier = self._score_to_tier(score)
            summary[tier] += 1

        return summary

    def _score_to_tier(self, score: float) -> ChurnTier:
        """Convert score to tier.

        Args:
            score: Churn score (0-100)

        Returns:
            ChurnTier (LOW, MEDIUM, HIGH)

        REQ-003: Tier boundaries (0-33, 34-66, 67-100)
        """
        if score < 34:
            return ChurnTier.LOW
        elif score < 67:
            return ChurnTier.MEDIUM
        else:
            return ChurnTier.HIGH

    def _compute_intervention(
        self,
        score: float,
        tier: ChurnTier,
        features: Dict,
    ) -> Optional[ChurnIntervention]:
        """Compute recommended intervention for at-risk customer.

        Args:
            score: Churn risk score
            tier: Churn tier
            features: Feature dict

        Returns:
            ChurnIntervention or None

        REQ-004: Recommend Churn Interventions
        """
        if tier == ChurnTier.LOW:
            return None  # No intervention needed

        # Get LTV estimate from features (if available)
        ltv = features.get("historical_ltv", 100.0)
        days_since_purchase = features.get("days_since_last_purchase", 30.0)

        # Decision tree for intervention
        if tier == ChurnTier.HIGH:
            if ltv > 500:
                # High-value, high-risk: VIP reactivation
                return ChurnIntervention(
                    intervention_type="vip_upgrade",
                    description="Offer VIP service and personalized support",
                    confidence=0.8,
                )
            else:
                # Lower-value: email offer
                discount = 10 + (score - 67) * 0.3  # Scale with risk
                return ChurnIntervention(
                    intervention_type="email_offer",
                    description=f"Send targeted email offer with {discount:.0f}% discount",
                    recommended_discount=min(discount, 30),
                    confidence=0.7,
                )

        elif tier == ChurnTier.MEDIUM:
            if days_since_purchase > 60:
                # Long time since purchase: product recommendation
                return ChurnIntervention(
                    intervention_type="product_recommendation",
                    description="Recommend products from preferred categories",
                    confidence=0.6,
                )
            else:
                # Recent activity: nurture email
                return ChurnIntervention(
                    intervention_type="email_offer",
                    description="Send nurture email with personalized content",
                    recommended_discount=5,
                    confidence=0.6,
                )

        return None

    @staticmethod
    def _features_to_dict(features) -> Dict:
        """Convert ChurnFeatures object to dict for explainer.

        Args:
            features: ChurnFeatures object

        Returns:
            Dict with feature names and values
        """
        return {
            "days_since_last_purchase": features.days_since_last_purchase,
            "purchase_frequency_30d": features.purchase_frequency_30d,
            "average_order_value": features.average_order_value,
            "cohort_churn_rate": features.cohort_churn_rate,
            "session_engagement_30d": features.session_engagement_30d,
            "return_rate": features.return_rate,
            "loyalty_tier": features.loyalty_tier,
        }
