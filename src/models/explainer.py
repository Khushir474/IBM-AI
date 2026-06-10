"""Explainability and feature attribution for model predictions."""

import logging
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FactorDirection(str, Enum):
    """Direction of feature contribution."""

    INCREASES = "increases"  # Higher feature value → higher prediction
    DECREASES = "decreases"  # Higher feature value → lower prediction
    NEUTRAL = "neutral"  # Feature has minimal impact


@dataclass
class ExplainabilityFactor:
    """A single factor explaining a prediction."""

    feature_name: str
    description: str  # Human-readable description
    contribution_score: float  # 0-100, higher = more important
    direction: FactorDirection  # Whether it increases or decreases prediction
    supporting_value: Optional[float] = None  # Actual feature value
    benchmark_value: Optional[float] = None  # Cohort/segment benchmark for comparison


class Explainer:
    """Generate human-readable explanations for model predictions."""

    def __init__(self, model_repository=None):
        """Initialize explainer.

        Args:
            model_repository: Optional ModelRepository for model introspection
        """
        self.repository = model_repository

    def explain_churn_score(
        self,
        customer_id: str,
        score: float,
        features: Dict[str, float],
        top_n: int = 3,
    ) -> List[ExplainabilityFactor]:
        """Explain churn risk score with human-readable factors.

        Args:
            customer_id: Customer ID (for context)
            score: Churn score (0-100)
            features: Dict with feature names and values
            top_n: Number of top factors to return

        Returns:
            List of ExplainabilityFactor objects
        """
        factors = []

        # Feature -> description mapping with direction
        feature_descriptions = {
            "days_since_last_purchase": {
                "desc": "Days since last purchase",
                "direction": FactorDirection.INCREASES,
                "threshold": 60,
            },
            "purchase_frequency_30d": {
                "desc": "Purchase frequency (last 30 days)",
                "direction": FactorDirection.DECREASES,
                "threshold": 2,
            },
            "average_order_value": {
                "desc": "Average order value",
                "direction": FactorDirection.DECREASES,
                "threshold": 100,
            },
            "cohort_churn_rate": {
                "desc": "Cohort churn rate",
                "direction": FactorDirection.INCREASES,
                "threshold": 0.15,
            },
            "session_engagement_30d": {
                "desc": "Session engagement (last 30 days)",
                "direction": FactorDirection.DECREASES,
                "threshold": 5,
            },
            "return_rate": {
                "desc": "Return rate",
                "direction": FactorDirection.INCREASES,
                "threshold": 0.1,
            },
            "loyalty_tier": {
                "desc": "Loyalty tier",
                "direction": FactorDirection.DECREASES,
                "threshold": 1,
            },
        }

        # Compute importance scores based on feature magnitude and direction
        for feat_name, feat_value in features.items():
            if feat_name not in feature_descriptions:
                continue

            desc_info = feature_descriptions[feat_name]
            threshold = desc_info.get("threshold", 0)
            direction = desc_info["direction"]

            # Compute contribution: how much this feature deviates from threshold
            deviation = abs(feat_value - threshold)
            # Normalize to 0-100 scale
            contribution = min(100, (deviation / max(threshold, 1.0)) * 50)

            # Adjust if direction matches the prediction
            if direction == FactorDirection.INCREASES and score > 50:
                contribution *= score / 100
            elif direction == FactorDirection.DECREASES and score < 50:
                contribution *= (100 - score) / 100

            factors.append(
                ExplainabilityFactor(
                    feature_name=feat_name,
                    description=self._format_churn_description(
                        desc_info["desc"], feat_value
                    ),
                    contribution_score=contribution,
                    direction=direction,
                    supporting_value=feat_value,
                    benchmark_value=threshold,
                )
            )

        # Sort by contribution and return top N
        factors.sort(key=lambda x: x.contribution_score, reverse=True)
        return factors[:top_n]

    def explain_ltv_prediction(
        self,
        customer_id: str,
        predictions: Dict[str, float],
        features: Dict[str, float],
        top_n: int = 3,
    ) -> List[ExplainabilityFactor]:
        """Explain LTV predictions with human-readable factors.

        Args:
            customer_id: Customer ID
            predictions: LTV predictions (ltv_7day, etc.)
            features: Dict with feature names and values
            top_n: Number of top factors to return

        Returns:
            List of ExplainabilityFactor objects
        """
        factors = []

        feature_descriptions = {
            "historical_ltv": {
                "desc": "Historical customer value",
                "direction": FactorDirection.INCREASES,
            },
            "cohort_avg_ltv": {
                "desc": "Cohort average LTV",
                "direction": FactorDirection.INCREASES,
            },
            "cumulative_orders": {
                "desc": "Cumulative orders",
                "direction": FactorDirection.INCREASES,
            },
            "repeat_purchase_rate": {
                "desc": "Repeat purchase rate",
                "direction": FactorDirection.INCREASES,
            },
            "seasonality_index": {
                "desc": "Seasonality index",
                "direction": FactorDirection.NEUTRAL,
            },
            "loyalty_tier": {
                "desc": "Loyalty tier",
                "direction": FactorDirection.INCREASES,
            },
        }

        avg_90day_ltv = predictions.get("ltv_90day", 0)

        for feat_name, feat_value in features.items():
            if feat_name not in feature_descriptions:
                continue

            desc_info = feature_descriptions[feat_name]
            direction = desc_info["direction"]

            # Contribution based on feature relevance to high LTV
            if direction == FactorDirection.INCREASES:
                contribution = min(100, feat_value * 10)
            elif direction == FactorDirection.DECREASES:
                contribution = min(100, (1 - feat_value) * 10 if feat_value < 1 else 0)
            else:
                contribution = 25

            factors.append(
                ExplainabilityFactor(
                    feature_name=feat_name,
                    description=self._format_ltv_description(desc_info["desc"], feat_value),
                    contribution_score=contribution,
                    direction=direction,
                    supporting_value=feat_value,
                    benchmark_value=avg_90day_ltv,
                )
            )

        factors.sort(key=lambda x: x.contribution_score, reverse=True)
        return factors[:top_n]

    def explain_cart_abandonment(
        self,
        customer_id: str,
        product_id: str,
        score: float,
        features: Dict[str, float],
        top_n: int = 3,
    ) -> List[ExplainabilityFactor]:
        """Explain cart abandonment with human-readable factors.

        Args:
            customer_id: Customer ID
            product_id: Product ID
            score: Recovery probability (0-100)
            features: Dict with feature names and values
            top_n: Number of top factors to return

        Returns:
            List of ExplainabilityFactor objects
        """
        factors = []

        feature_descriptions = {
            "cart_value": {
                "desc": "Cart value",
                "direction": FactorDirection.DECREASES,  # Higher value, harder to recover
                "threshold": 150,
            },
            "cart_item_count": {
                "desc": "Items in cart",
                "direction": FactorDirection.DECREASES,
                "threshold": 3,
            },
            "item_avg_recovery_rate": {
                "desc": "Item average recovery rate",
                "direction": FactorDirection.INCREASES,
                "threshold": 0.3,
            },
            "customer_repeat_buyer": {
                "desc": "Repeat buyer status",
                "direction": FactorDirection.INCREASES,
                "threshold": 1,
            },
            "time_since_abandon": {
                "desc": "Time since abandonment",
                "direction": FactorDirection.DECREASES,  # Older carts harder to recover
                "threshold": 2,
            },
            "previous_abandon_count": {
                "desc": "Previous abandonment count",
                "direction": FactorDirection.DECREASES,
                "threshold": 1,
            },
            "shipping_cost_ratio": {
                "desc": "Shipping cost ratio",
                "direction": FactorDirection.DECREASES,  # Higher ratio, harder to recover
                "threshold": 0.15,
            },
        }

        for feat_name, feat_value in features.items():
            if feat_name not in feature_descriptions:
                continue

            desc_info = feature_descriptions[feat_name]
            threshold = desc_info.get("threshold", 0)
            direction = desc_info["direction"]

            # Contribution based on deviation from threshold
            deviation = abs(feat_value - threshold)
            contribution = min(100, (deviation / max(threshold, 1.0)) * 40)

            # Adjust based on recovery score
            if direction == FactorDirection.INCREASES and score > 50:
                contribution *= (score / 100)
            elif direction == FactorDirection.DECREASES and score < 50:
                contribution *= ((100 - score) / 100)

            factors.append(
                ExplainabilityFactor(
                    feature_name=feat_name,
                    description=self._format_cart_description(desc_info["desc"], feat_value),
                    contribution_score=contribution,
                    direction=direction,
                    supporting_value=feat_value,
                    benchmark_value=threshold,
                )
            )

        factors.sort(key=lambda x: x.contribution_score, reverse=True)
        return factors[:top_n]

    def explain_price_recommendation(
        self,
        product_id: str,
        recommendation: Dict[str, float],
        features: Dict[str, float],
        top_n: int = 3,
    ) -> List[ExplainabilityFactor]:
        """Explain pricing recommendation with human-readable factors.

        Args:
            product_id: Product ID
            recommendation: Price recommendation dict
            features: Dict with feature names and values
            top_n: Number of top factors to return

        Returns:
            List of ExplainabilityFactor objects
        """
        factors = []

        feature_descriptions = {
            "inventory_days_supply": {
                "desc": "Inventory days supply",
                "direction": FactorDirection.INCREASES,  # More stock → discount more
                "threshold": 30,
            },
            "price_elasticity": {
                "desc": "Price elasticity",
                "direction": FactorDirection.INCREASES,
                "threshold": 0.5,
            },
            "competitor_price_gap": {
                "desc": "Competitor price gap",
                "direction": FactorDirection.INCREASES,  # If higher, reduce price
                "threshold": 0,
            },
            "product_margin_pct": {
                "desc": "Product margin %",
                "direction": FactorDirection.DECREASES,  # High margin → preserve
                "threshold": 0.35,
            },
            "weekly_units_sold": {
                "desc": "Weekly units sold",
                "direction": FactorDirection.DECREASES,  # High velocity → preserve price
                "threshold": 100,
            },
            "weekly_return_rate": {
                "desc": "Weekly return rate",
                "direction": FactorDirection.DECREASES,  # High returns → reduce price?
                "threshold": 0.05,
            },
        }

        for feat_name, feat_value in features.items():
            if feat_name not in feature_descriptions:
                continue

            desc_info = feature_descriptions[feat_name]
            threshold = desc_info.get("threshold", 0)
            direction = desc_info["direction"]

            deviation = abs(feat_value - threshold)
            contribution = min(100, (deviation / max(threshold, 0.1)) * 30)

            factors.append(
                ExplainabilityFactor(
                    feature_name=feat_name,
                    description=self._format_pricing_description(
                        desc_info["desc"], feat_value
                    ),
                    contribution_score=contribution,
                    direction=direction,
                    supporting_value=feat_value,
                    benchmark_value=threshold,
                )
            )

        factors.sort(key=lambda x: x.contribution_score, reverse=True)
        return factors[:top_n]

    @staticmethod
    def _format_churn_description(base_desc: str, value: float) -> str:
        """Format human-readable description for churn factor."""
        if "days" in base_desc.lower():
            return f"{base_desc}: {int(value)} days"
        elif "frequency" in base_desc.lower():
            return f"{base_desc}: {value:.1f} purchases"
        elif "value" in base_desc.lower():
            return f"{base_desc}: ${value:.2f}"
        elif "rate" in base_desc.lower():
            return f"{base_desc}: {value*100:.1f}%"
        elif "engagement" in base_desc.lower():
            return f"{base_desc}: {value:.1f} sessions"
        else:
            return f"{base_desc}: {value:.2f}"

    @staticmethod
    def _format_ltv_description(base_desc: str, value: float) -> str:
        """Format human-readable description for LTV factor."""
        if "ltv" in base_desc.lower() or "value" in base_desc.lower():
            return f"{base_desc}: ${value:.2f}"
        elif "orders" in base_desc.lower():
            return f"{base_desc}: {int(value)}"
        elif "rate" in base_desc.lower() or "index" in base_desc.lower():
            return f"{base_desc}: {value:.2f}"
        elif "tier" in base_desc.lower():
            return f"{base_desc}: {int(value)}"
        else:
            return f"{base_desc}: {value:.2f}"

    @staticmethod
    def _format_cart_description(base_desc: str, value: float) -> str:
        """Format human-readable description for cart factor."""
        if "value" in base_desc.lower():
            return f"{base_desc}: ${value:.2f}"
        elif "count" in base_desc.lower() or "item" in base_desc.lower():
            return f"{base_desc}: {int(value)}"
        elif "rate" in base_desc.lower() or "ratio" in base_desc.lower():
            return f"{base_desc}: {value*100:.1f}%"
        elif "time" in base_desc.lower():
            return f"{base_desc}: {value:.1f} hours"
        else:
            return f"{base_desc}: {value:.2f}"

    @staticmethod
    def _format_pricing_description(base_desc: str, value: float) -> str:
        """Format human-readable description for pricing factor."""
        if "margin" in base_desc.lower():
            return f"{base_desc}: {value*100:.1f}%"
        elif "gap" in base_desc.lower() or "price" in base_desc.lower():
            return f"{base_desc}: ${value:.2f}"
        elif "units" in base_desc.lower():
            return f"{base_desc}: {int(value)} units/week"
        elif "rate" in base_desc.lower():
            return f"{base_desc}: {value*100:.1f}%"
        elif "days" in base_desc.lower():
            return f"{base_desc}: {int(value)} days"
        else:
            return f"{base_desc}: {value:.2f}"
