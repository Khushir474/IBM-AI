"""ML model inference for predictions."""

import logging
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ChurnFeatures:
    """Features for churn prediction."""

    days_since_last_purchase: float
    purchase_frequency_30d: float
    average_order_value: float
    product_category_affinity: List[float]
    cohort_churn_rate: float
    session_engagement_30d: float
    return_rate: float
    loyalty_tier: float

    def to_vector(self) -> np.ndarray:
        """Convert to feature vector for model input."""
        # Flatten category affinity and concatenate
        features = [
            self.days_since_last_purchase,
            self.purchase_frequency_30d,
            self.average_order_value,
            self.cohort_churn_rate,
            self.session_engagement_30d,
            self.return_rate,
            self.loyalty_tier,
        ]
        # Add category affinity features
        features.extend(self.product_category_affinity)
        return np.array([features])


@dataclass
class LTVFeatures:
    """Features for LTV prediction."""

    historical_ltv: float
    cohort_avg_ltv: float
    cumulative_orders: float
    product_category_spend: List[float]
    repeat_purchase_rate: float
    seasonality_index: float
    loyalty_tier: float

    def to_vector(self) -> np.ndarray:
        """Convert to feature vector for model input."""
        features = [
            self.historical_ltv,
            self.cohort_avg_ltv,
            self.cumulative_orders,
            self.repeat_purchase_rate,
            self.seasonality_index,
            self.loyalty_tier,
        ]
        features.extend(self.product_category_spend)
        return np.array([features])


@dataclass
class CartFeatures:
    """Features for cart abandonment recovery prediction."""

    cart_value: float
    cart_item_count: float
    item_avg_recovery_rate: float
    customer_repeat_buyer: float
    time_since_abandon: float
    previous_abandon_count: float
    shipping_cost_ratio: float
    device_type: float

    def to_vector(self) -> np.ndarray:
        """Convert to feature vector for model input."""
        features = [
            self.cart_value,
            self.cart_item_count,
            self.item_avg_recovery_rate,
            self.customer_repeat_buyer,
            self.time_since_abandon,
            self.previous_abandon_count,
            self.shipping_cost_ratio,
            self.device_type,
        ]
        return np.array([features])


@dataclass
class PricingFeatures:
    """Features for pricing optimization."""

    inventory_days_supply: float
    price_elasticity: float
    competitor_price_gap: float
    product_margin_pct: float
    weekly_units_sold: float
    weekly_return_rate: float

    def to_vector(self) -> np.ndarray:
        """Convert to feature vector for model input."""
        features = [
            self.inventory_days_supply,
            self.price_elasticity,
            self.competitor_price_gap,
            self.product_margin_pct,
            self.weekly_units_sold,
            self.weekly_return_rate,
        ]
        return np.array([features])


class ModelInference:
    """Perform ML model inference for predictions."""

    def __init__(self, model_repository):
        """Initialize inference engine.

        Args:
            model_repository: ModelRepository instance for loading models
        """
        self.repository = model_repository

    def predict_churn_score(self, features: ChurnFeatures) -> float:
        """Predict churn risk score (0-100).

        Args:
            features: ChurnFeatures object

        Returns:
            Churn risk score (0=very low risk, 100=very high risk)
        """
        try:
            model = self.repository.load_model("churn")
        except FileNotFoundError:
            logger.warning("Churn model not found, returning default prediction")
            return 50.0

        # Get prediction from model
        feature_vector = features.to_vector()
        try:
            # Try predict_proba for probabilistic models
            if hasattr(model, "predict_proba"):
                prob = model.predict_proba(feature_vector)[0][1]
                score = prob * 100
            else:
                # Fallback to predict
                pred = model.predict(feature_vector)[0]
                score = pred * 100 if isinstance(pred, (int, float)) else pred
            # Clamp to [0, 100]
            return float(max(0, min(100, score)))
        except Exception as e:
            logger.error(f"Error predicting churn score: {e}")
            return 50.0

    def predict_ltv_horizons(self, features: LTVFeatures) -> Dict[str, float]:
        """Predict customer LTV at multiple time horizons.

        Args:
            features: LTVFeatures object

        Returns:
            Dict with keys: 'ltv_7day', 'ltv_30day', 'ltv_90day', 'ltv_365day'
        """
        try:
            model = self.repository.load_model("ltv")
        except FileNotFoundError:
            logger.warning("LTV model not found, returning default predictions")
            return {
                "ltv_7day": 0.0,
                "ltv_30day": 0.0,
                "ltv_90day": 0.0,
                "ltv_365day": 0.0,
            }

        feature_vector = features.to_vector()
        try:
            if hasattr(model, "predict"):
                prediction = model.predict(feature_vector)[0]
                # For multi-output model, expect 4 values; for single output, scale
                if isinstance(prediction, (list, np.ndarray)):
                    if len(prediction) == 4:
                        return {
                            "ltv_7day": float(max(0, prediction[0])),
                            "ltv_30day": float(max(0, prediction[1])),
                            "ltv_90day": float(max(0, prediction[2])),
                            "ltv_365day": float(max(0, prediction[3])),
                        }
                    elif len(prediction) >= 1:
                        # Single prediction, scale by factors
                        base = float(max(0, prediction[0]))
                        return {
                            "ltv_7day": base * 0.08,
                            "ltv_30day": base * 0.25,
                            "ltv_90day": base * 0.75,
                            "ltv_365day": base,
                        }
                # Scalar prediction
                base = float(prediction)
                return {
                    "ltv_7day": base * 0.08,
                    "ltv_30day": base * 0.25,
                    "ltv_90day": base * 0.75,
                    "ltv_365day": base,
                }
        except Exception as e:
            logger.error(f"Error predicting LTV: {e}")
            return {
                "ltv_7day": 0.0,
                "ltv_30day": 0.0,
                "ltv_90day": 0.0,
                "ltv_365day": 0.0,
            }

    def predict_recovery_probability(self, features: CartFeatures) -> float:
        """Predict cart recovery probability (0-100).

        Args:
            features: CartFeatures object

        Returns:
            Recovery probability score (0=unlikely, 100=very likely)
        """
        try:
            model = self.repository.load_model("recovery")
        except FileNotFoundError:
            logger.warning("Recovery model not found, returning default prediction")
            return 50.0

        feature_vector = features.to_vector()
        try:
            if hasattr(model, "predict_proba"):
                prob = model.predict_proba(feature_vector)[0][1]
                score = prob * 100
            else:
                pred = model.predict(feature_vector)[0]
                score = pred * 100 if isinstance(pred, (int, float)) else pred
            return float(max(0, min(100, score)))
        except Exception as e:
            logger.error(f"Error predicting recovery probability: {e}")
            return 50.0

    def recommend_price(self, features: PricingFeatures) -> Dict[str, float]:
        """Recommend price for a product.

        Args:
            features: PricingFeatures object

        Returns:
            Dict with keys: 'recommended_price', 'discount_pct'
        """
        try:
            model = self.repository.load_model("pricing")
        except FileNotFoundError:
            logger.warning("Pricing model not found, returning default recommendation")
            return {"recommended_price": 0.0, "discount_pct": 0.0}

        feature_vector = features.to_vector()
        try:
            if hasattr(model, "predict"):
                prediction = model.predict(feature_vector)[0]
                if isinstance(prediction, (list, np.ndarray)):
                    if len(prediction) >= 2:
                        return {
                            "recommended_price": float(max(0, prediction[0])),
                            "discount_pct": float(max(0, min(100, prediction[1]))),
                        }
                    elif len(prediction) == 1:
                        price = float(max(0, prediction[0]))
                        return {
                            "recommended_price": price,
                            "discount_pct": 0.0,
                        }
                # Scalar prediction
                price = float(prediction)
                return {
                    "recommended_price": max(0, price),
                    "discount_pct": 0.0,
                }
        except Exception as e:
            logger.error(f"Error predicting price: {e}")
            return {"recommended_price": 0.0, "discount_pct": 0.0}

    def predict_batch_churn(self, feature_list: List[ChurnFeatures]) -> List[float]:
        """Batch prediction for churn scores (efficient).

        Args:
            feature_list: List of ChurnFeatures objects

        Returns:
            List of churn scores
        """
        if not feature_list:
            return []

        try:
            model = self.repository.load_model("churn")
        except FileNotFoundError:
            logger.warning("Churn model not found, returning default predictions")
            return [50.0] * len(feature_list)

        try:
            feature_vectors = np.vstack([f.to_vector() for f in feature_list])
            if hasattr(model, "predict_proba"):
                probs = model.predict_proba(feature_vectors)[:, 1]
                scores = probs * 100
            else:
                preds = model.predict(feature_vectors)
                scores = np.array(preds) * 100
            return [float(max(0, min(100, s))) for s in scores]
        except Exception as e:
            logger.error(f"Error in batch churn prediction: {e}")
            return [50.0] * len(feature_list)
