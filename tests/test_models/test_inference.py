"""Tests for ModelInference (Task 2.1)."""

import pytest
import numpy as np
import pickle
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock

from src.models.inference import (
    ModelInference,
    ChurnFeatures,
    LTVFeatures,
    CartFeatures,
    PricingFeatures,
)
from src.models.model_repository import ModelRepository


class MockProbabilisticModel:
    """Mock sklearn classifier with predict_proba."""

    def predict_proba(self, X):
        """Return mock probabilities."""
        n_samples = len(X) if len(X.shape) > 1 else 1
        # Return class 0 and class 1 probabilities
        probs = np.random.rand(n_samples, 2)
        probs = probs / probs.sum(axis=1, keepdims=True)
        return probs


class MockRegressionModel:
    """Mock sklearn regressor."""

    def predict(self, X):
        """Return mock regression predictions."""
        n_samples = len(X) if len(X.shape) > 1 else 1
        return np.random.rand(n_samples) * 100


class MockMultiOutputModel:
    """Mock model with multiple outputs."""

    def predict(self, X):
        """Return 4 outputs for LTV horizons (monotonically increasing)."""
        n_samples = len(X) if len(X.shape) > 1 else 1
        # Return monotonically increasing values: 100, 300, 750, 1000
        return np.array([[100.0, 300.0, 750.0, 1000.0]] * n_samples)


class TestChurnFeaturesVector:
    """Test ChurnFeatures to vector conversion."""

    def test_churn_features_creation(self):
        """Test creating ChurnFeatures."""
        features = ChurnFeatures(
            days_since_last_purchase=30.0,
            purchase_frequency_30d=5.0,
            average_order_value=150.0,
            product_category_affinity=[1.0, 0.0, 0.0],
            cohort_churn_rate=0.15,
            session_engagement_30d=10.0,
            return_rate=0.05,
            loyalty_tier=2.0,
        )
        assert features.days_since_last_purchase == 30.0
        assert len(features.product_category_affinity) == 3

    def test_churn_features_to_vector(self):
        """Test converting ChurnFeatures to numpy array."""
        features = ChurnFeatures(
            days_since_last_purchase=30.0,
            purchase_frequency_30d=5.0,
            average_order_value=150.0,
            product_category_affinity=[1.0, 0.0, 0.0],
            cohort_churn_rate=0.15,
            session_engagement_30d=10.0,
            return_rate=0.05,
            loyalty_tier=2.0,
        )
        vector = features.to_vector()
        assert isinstance(vector, np.ndarray)
        assert vector.shape == (1, 10)  # 7 features + 3 category features

    def test_churn_features_empty_categories(self):
        """Test ChurnFeatures with empty category affinity."""
        features = ChurnFeatures(
            days_since_last_purchase=30.0,
            purchase_frequency_30d=5.0,
            average_order_value=150.0,
            product_category_affinity=[],
            cohort_churn_rate=0.15,
            session_engagement_30d=10.0,
            return_rate=0.05,
            loyalty_tier=2.0,
        )
        vector = features.to_vector()
        assert vector.shape == (1, 7)


class TestLTVFeaturesVector:
    """Test LTVFeatures to vector conversion."""

    def test_ltv_features_creation(self):
        """Test creating LTVFeatures."""
        features = LTVFeatures(
            historical_ltv=500.0,
            cohort_avg_ltv=450.0,
            cumulative_orders=15.0,
            product_category_spend=[100.0, 200.0, 200.0],
            repeat_purchase_rate=0.8,
            seasonality_index=1.2,
            loyalty_tier=2.0,
        )
        assert features.historical_ltv == 500.0

    def test_ltv_features_to_vector(self):
        """Test converting LTVFeatures to numpy array."""
        features = LTVFeatures(
            historical_ltv=500.0,
            cohort_avg_ltv=450.0,
            cumulative_orders=15.0,
            product_category_spend=[100.0, 200.0, 200.0],
            repeat_purchase_rate=0.8,
            seasonality_index=1.2,
            loyalty_tier=2.0,
        )
        vector = features.to_vector()
        assert isinstance(vector, np.ndarray)
        assert vector.shape == (1, 9)  # 6 features + 3 category features


class TestCartFeaturesVector:
    """Test CartFeatures to vector conversion."""

    def test_cart_features_creation(self):
        """Test creating CartFeatures."""
        features = CartFeatures(
            cart_value=250.0,
            cart_item_count=3.0,
            item_avg_recovery_rate=0.35,
            customer_repeat_buyer=1.0,
            time_since_abandon=2.5,
            previous_abandon_count=1.0,
            shipping_cost_ratio=0.15,
            device_type=1.0,
        )
        assert features.cart_value == 250.0

    def test_cart_features_to_vector(self):
        """Test converting CartFeatures to numpy array."""
        features = CartFeatures(
            cart_value=250.0,
            cart_item_count=3.0,
            item_avg_recovery_rate=0.35,
            customer_repeat_buyer=1.0,
            time_since_abandon=2.5,
            previous_abandon_count=1.0,
            shipping_cost_ratio=0.15,
            device_type=1.0,
        )
        vector = features.to_vector()
        assert isinstance(vector, np.ndarray)
        assert vector.shape == (1, 8)


class TestPricingFeaturesVector:
    """Test PricingFeatures to vector conversion."""

    def test_pricing_features_creation(self):
        """Test creating PricingFeatures."""
        features = PricingFeatures(
            inventory_days_supply=45.0,
            price_elasticity=0.8,
            competitor_price_gap=5.0,
            product_margin_pct=0.35,
            weekly_units_sold=150.0,
            weekly_return_rate=0.03,
        )
        assert features.inventory_days_supply == 45.0

    def test_pricing_features_to_vector(self):
        """Test converting PricingFeatures to numpy array."""
        features = PricingFeatures(
            inventory_days_supply=45.0,
            price_elasticity=0.8,
            competitor_price_gap=5.0,
            product_margin_pct=0.35,
            weekly_units_sold=150.0,
            weekly_return_rate=0.03,
        )
        vector = features.to_vector()
        assert isinstance(vector, np.ndarray)
        assert vector.shape == (1, 6)


class TestChurnPrediction:
    """Test churn score prediction."""

    def test_churn_prediction_with_model(self):
        """Test churn prediction with mock model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            # Create and save mock model
            model = MockProbabilisticModel()
            model_path = Path(tmpdir) / "churn.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            inference = ModelInference(repo)

            features = ChurnFeatures(
                days_since_last_purchase=30.0,
                purchase_frequency_30d=5.0,
                average_order_value=150.0,
                product_category_affinity=[1.0, 0.0, 0.0],
                cohort_churn_rate=0.15,
                session_engagement_30d=10.0,
                return_rate=0.05,
                loyalty_tier=2.0,
            )

            score = inference.predict_churn_score(features)
            assert isinstance(score, float)
            assert 0 <= score <= 100

    def test_churn_prediction_missing_model(self):
        """Test churn prediction with missing model returns default."""
        repo = ModelRepository()  # Empty repo
        inference = ModelInference(repo)

        features = ChurnFeatures(
            days_since_last_purchase=30.0,
            purchase_frequency_30d=5.0,
            average_order_value=150.0,
            product_category_affinity=[1.0, 0.0, 0.0],
            cohort_churn_rate=0.15,
            session_engagement_30d=10.0,
            return_rate=0.05,
            loyalty_tier=2.0,
        )

        score = inference.predict_churn_score(features)
        # Should return default (50.0)
        assert score == 50.0

    def test_churn_prediction_range(self):
        """Test churn prediction respects [0, 100] bounds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            model = MockProbabilisticModel()
            model_path = Path(tmpdir) / "churn.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            inference = ModelInference(repo)

            features = ChurnFeatures(
                days_since_last_purchase=100.0,
                purchase_frequency_30d=1.0,
                average_order_value=50.0,
                product_category_affinity=[1.0, 0.0, 0.0],
                cohort_churn_rate=0.5,
                session_engagement_30d=1.0,
                return_rate=0.2,
                loyalty_tier=1.0,
            )

            # Run multiple predictions
            for _ in range(10):
                score = inference.predict_churn_score(features)
                assert 0 <= score <= 100


class TestLTVPrediction:
    """Test LTV prediction at multiple horizons."""

    def test_ltv_prediction_with_model(self):
        """Test LTV prediction with mock model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            # Create and save mock model
            model = MockMultiOutputModel()
            model_path = Path(tmpdir) / "ltv.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            inference = ModelInference(repo)

            features = LTVFeatures(
                historical_ltv=500.0,
                cohort_avg_ltv=450.0,
                cumulative_orders=15.0,
                product_category_spend=[100.0, 200.0, 200.0],
                repeat_purchase_rate=0.8,
                seasonality_index=1.2,
                loyalty_tier=2.0,
            )

            predictions = inference.predict_ltv_horizons(features)
            assert "ltv_7day" in predictions
            assert "ltv_30day" in predictions
            assert "ltv_90day" in predictions
            assert "ltv_365day" in predictions

    def test_ltv_prediction_horizons_monotonic(self):
        """Test LTV predictions are monotonically increasing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            model = MockMultiOutputModel()
            model_path = Path(tmpdir) / "ltv.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            inference = ModelInference(repo)

            features = LTVFeatures(
                historical_ltv=500.0,
                cohort_avg_ltv=450.0,
                cumulative_orders=15.0,
                product_category_spend=[100.0, 200.0, 200.0],
                repeat_purchase_rate=0.8,
                seasonality_index=1.2,
                loyalty_tier=2.0,
            )

            predictions = inference.predict_ltv_horizons(features)
            # Model returns [100, 300, 750, 1000] which is monotonic
            assert predictions["ltv_7day"] <= predictions["ltv_30day"]
            assert predictions["ltv_30day"] <= predictions["ltv_90day"]
            assert predictions["ltv_90day"] <= predictions["ltv_365day"]

    def test_ltv_prediction_missing_model(self):
        """Test LTV prediction with missing model returns zeros."""
        repo = ModelRepository()
        inference = ModelInference(repo)

        features = LTVFeatures(
            historical_ltv=500.0,
            cohort_avg_ltv=450.0,
            cumulative_orders=15.0,
            product_category_spend=[100.0, 200.0, 200.0],
            repeat_purchase_rate=0.8,
            seasonality_index=1.2,
            loyalty_tier=2.0,
        )

        predictions = inference.predict_ltv_horizons(features)
        assert all(v == 0.0 for v in predictions.values())


class TestRecoveryPrediction:
    """Test cart recovery probability prediction."""

    def test_recovery_prediction_with_model(self):
        """Test recovery prediction with mock model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            model = MockProbabilisticModel()
            model_path = Path(tmpdir) / "recovery.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            inference = ModelInference(repo)

            features = CartFeatures(
                cart_value=250.0,
                cart_item_count=3.0,
                item_avg_recovery_rate=0.35,
                customer_repeat_buyer=1.0,
                time_since_abandon=2.5,
                previous_abandon_count=1.0,
                shipping_cost_ratio=0.15,
                device_type=1.0,
            )

            score = inference.predict_recovery_probability(features)
            assert isinstance(score, float)
            assert 0 <= score <= 100

    def test_recovery_prediction_missing_model(self):
        """Test recovery prediction with missing model returns default."""
        repo = ModelRepository()
        inference = ModelInference(repo)

        features = CartFeatures(
            cart_value=250.0,
            cart_item_count=3.0,
            item_avg_recovery_rate=0.35,
            customer_repeat_buyer=1.0,
            time_since_abandon=2.5,
            previous_abandon_count=1.0,
            shipping_cost_ratio=0.15,
            device_type=1.0,
        )

        score = inference.predict_recovery_probability(features)
        assert score == 50.0


class TestPricingRecommendation:
    """Test pricing recommendation."""

    def test_pricing_recommendation_with_model(self):
        """Test pricing recommendation with mock model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            model = MockRegressionModel()
            model_path = Path(tmpdir) / "pricing.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            inference = ModelInference(repo)

            features = PricingFeatures(
                inventory_days_supply=45.0,
                price_elasticity=0.8,
                competitor_price_gap=5.0,
                product_margin_pct=0.35,
                weekly_units_sold=150.0,
                weekly_return_rate=0.03,
            )

            recommendation = inference.recommend_price(features)
            assert "recommended_price" in recommendation
            assert "discount_pct" in recommendation

    def test_pricing_recommendation_missing_model(self):
        """Test pricing recommendation with missing model returns defaults."""
        repo = ModelRepository()
        inference = ModelInference(repo)

        features = PricingFeatures(
            inventory_days_supply=45.0,
            price_elasticity=0.8,
            competitor_price_gap=5.0,
            product_margin_pct=0.35,
            weekly_units_sold=150.0,
            weekly_return_rate=0.03,
        )

        recommendation = inference.recommend_price(features)
        assert recommendation["recommended_price"] == 0.0
        assert recommendation["discount_pct"] == 0.0


class TestBatchInference:
    """Test batch prediction functionality."""

    def test_batch_churn_prediction(self):
        """Test batch churn prediction is more efficient."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            model = MockProbabilisticModel()
            model_path = Path(tmpdir) / "churn.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            inference = ModelInference(repo)

            # Create multiple features
            features_list = [
                ChurnFeatures(
                    days_since_last_purchase=30.0 + i,
                    purchase_frequency_30d=5.0 - i,
                    average_order_value=150.0,
                    product_category_affinity=[1.0, 0.0, 0.0],
                    cohort_churn_rate=0.15,
                    session_engagement_30d=10.0,
                    return_rate=0.05,
                    loyalty_tier=2.0,
                )
                for i in range(5)
            ]

            scores = inference.predict_batch_churn(features_list)
            assert len(scores) == 5
            assert all(0 <= s <= 100 for s in scores)

    def test_batch_churn_empty_list(self):
        """Test batch prediction with empty list."""
        repo = ModelRepository()
        inference = ModelInference(repo)

        scores = inference.predict_batch_churn([])
        assert scores == []

    def test_batch_churn_missing_model(self):
        """Test batch prediction with missing model."""
        repo = ModelRepository()
        inference = ModelInference(repo)

        features_list = [
            ChurnFeatures(
                days_since_last_purchase=30.0,
                purchase_frequency_30d=5.0,
                average_order_value=150.0,
                product_category_affinity=[1.0, 0.0, 0.0],
                cohort_churn_rate=0.15,
                session_engagement_30d=10.0,
                return_rate=0.05,
                loyalty_tier=2.0,
            )
        ]

        scores = inference.predict_batch_churn(features_list)
        assert all(s == 50.0 for s in scores)
