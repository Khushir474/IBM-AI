"""LTV prediction service (Task 3.2)."""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class LTVPredictions:
    """LTV predictions for a customer."""

    customer_id: str
    ltv_7day: float
    ltv_30day: float
    ltv_90day: float
    ltv_365day: float
    factors: List[Dict] = None  # Top drivers


@dataclass
class LTVCohort:
    """Customer cohort by predicted LTV."""

    cohort_name: str
    size: int
    avg_ltv: float
    avg_ltv_7day: float
    avg_ltv_30day: float
    avg_ltv_90day: float
    avg_ltv_365day: float
    characteristics: Dict = None  # e.g., avg_order_value, repeat_rate


@dataclass
class HighPotentialCustomer:
    """New customer flagged as high-potential."""

    customer_id: str
    days_as_customer: int
    predicted_ltv_90day: float
    confidence: float  # 0-1
    signals: List[str]  # e.g., ["high_first_purchase", "repeat_within_3_days"]


@dataclass
class ModelAccuracyMetrics:
    """LTV model accuracy metrics."""

    mean_absolute_error: float
    root_mean_squared_error: float
    mean_absolute_percentage_error: float
    calibration_score: Optional[float] = None
    accuracy_by_cohort: Optional[Dict[str, float]] = None  # Cohort -> MAE


class LTVService:
    """Business logic for LTV prediction, cohort analysis, high-potential flagging."""

    def __init__(
        self,
        feature_engineer,
        model_inference,
        explainer,
        cache_manager=None,
    ):
        """Initialize LTVService.

        Args:
            feature_engineer: LTVFeatureEngineer instance
            model_inference: ModelInference instance
            explainer: Explainer instance
            cache_manager: Optional cache manager
        """
        self.feature_engineer = feature_engineer
        self.model_inference = model_inference
        self.explainer = explainer
        self.cache_manager = cache_manager

    def predict_ltv(self, customer_id: str) -> Optional[LTVPredictions]:
        """Predict customer LTV at multiple time horizons.

        Args:
            customer_id: Customer ID

        Returns:
            LTVPredictions with 4 horizons and drivers

        REQ-006: Predict Customer Lifetime Value at Multiple Time Horizons
        """
        try:
            # Compute features
            features = self.feature_engineer.compute_features(customer_id)
            if features is None:
                logger.warning(f"Could not compute LTV features for {customer_id}")
                return None

            # Get predictions
            predictions = self.model_inference.predict_ltv_horizons(features)

            # Get factors
            feature_dict = self._features_to_dict(features)
            factors = self.explainer.explain_ltv_prediction(
                customer_id=customer_id,
                predictions=predictions,
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

            return LTVPredictions(
                customer_id=customer_id,
                ltv_7day=predictions["ltv_7day"],
                ltv_30day=predictions["ltv_30day"],
                ltv_90day=predictions["ltv_90day"],
                ltv_365day=predictions["ltv_365day"],
                factors=factors_list,
            )

        except Exception as e:
            logger.error(f"Error predicting LTV for {customer_id}: {e}")
            return None

    def list_high_value_cohorts(self, limit: int = 20) -> List[LTVCohort]:
        """Identify and segment high-value customer cohorts.

        Args:
            limit: Number of top cohorts to return

        Returns:
            List of LTVCohort sorted by avg LTV descending

        REQ-007: Identify High-Value Customer Cohorts
        """
        # This would typically read from pre-computed cohort analytics (Iceberg)
        # For now, return empty list (to be integrated with DAOs)
        logger.info(f"Retrieving top {limit} LTV cohorts")
        return []

    def flag_new_high_potential(
        self,
        acquisition_hours: int = 24 * 7,
        limit: int = 100,
    ) -> List[HighPotentialCustomer]:
        """Flag new customers showing high-potential signals.

        Args:
            acquisition_hours: Hours since acquisition to consider "new"
            limit: Maximum number to return

        Returns:
            List of HighPotentialCustomer with confidence scores

        REQ-008: Flag Early Indicators of High-Value Customers
        """
        # This would typically query recent acquisitions and score them
        # For now, return empty list (to be integrated with DAOs)
        logger.info(f"Searching for high-potential customers acquired in last {acquisition_hours}h")
        return []

    def get_model_accuracy(
        self,
        historical_window_days: int = 90,
    ) -> Optional[ModelAccuracyMetrics]:
        """Get LTV model accuracy metrics.

        Args:
            historical_window_days: Days of historical data to evaluate

        Returns:
            ModelAccuracyMetrics with MAE, RMSE, calibration

        REQ-009: Compare Predicted vs. Actual LTV
        """
        try:
            # This would typically query Iceberg for historical predictions vs actuals
            # For now, return None (to be integrated with DAOs)
            logger.info(f"Computing LTV model accuracy for last {historical_window_days} days")
            return None

        except Exception as e:
            logger.error(f"Error computing model accuracy: {e}")
            return None

    @staticmethod
    def _features_to_dict(features) -> Dict:
        """Convert LTVFeatures object to dict for explainer.

        Args:
            features: LTVFeatures object

        Returns:
            Dict with feature names and values
        """
        return {
            "historical_ltv": features.historical_ltv,
            "cohort_avg_ltv": features.cohort_avg_ltv,
            "cumulative_orders": features.cumulative_orders,
            "repeat_purchase_rate": features.repeat_purchase_rate,
            "seasonality_index": features.seasonality_index,
            "loyalty_tier": features.loyalty_tier,
        }
