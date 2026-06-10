"""Tests for ModelRepository (Task 2.1)."""

import pytest
import pickle
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock

from src.models.model_repository import ModelRepository


class MockModel:
    """Mock ML model for testing."""

    def __init__(self, name: str = "mock"):
        self.name = name

    def predict_proba(self, X):
        """Mock predict_proba."""
        import numpy as np
        return np.array([[0.4, 0.6]] * len(X))

    def predict(self, X):
        """Mock predict."""
        import numpy as np
        return np.array([0.6] * len(X))


class TestModelRepositoryInitialization:
    """Test ModelRepository initialization."""

    def test_init_default_model_dir(self):
        """Test default model directory is created."""
        repo = ModelRepository()
        assert repo.model_dir == Path("./models")
        assert isinstance(repo._models, dict)
        assert len(repo._models) == 0

    def test_init_custom_model_dir(self):
        """Test custom model directory."""
        custom_dir = "/custom/models"
        repo = ModelRepository(model_dir=custom_dir)
        assert repo.model_dir == Path(custom_dir)

    def test_init_empty_cache(self):
        """Test cache starts empty."""
        repo = ModelRepository()
        assert repo.list_cached_models() == {}


class TestModelRepositoryLoading:
    """Test model loading and caching."""

    def test_load_model_success(self):
        """Test successful model loading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            # Create mock model file
            model = MockModel("churn")
            model_path = Path(tmpdir) / "churn.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            # Load model
            loaded = repo.load_model("churn")
            assert loaded is not None
            assert isinstance(loaded, MockModel)
            assert loaded.name == "churn"

    def test_load_model_with_version(self):
        """Test loading model with specific version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            # Create versioned model file
            model = MockModel("churn_v2")
            model_path = Path(tmpdir) / "churn_2024-06-10.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            # Load model
            loaded = repo.load_model("churn", model_version="2024-06-10")
            assert loaded is not None

    def test_load_model_not_found(self):
        """Test loading non-existent model raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            with pytest.raises(FileNotFoundError):
                repo.load_model("nonexistent")

    def test_load_model_invalid_file(self):
        """Test loading corrupted model file raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            # Create invalid pickle file
            model_path = Path(tmpdir) / "bad_model.pkl"
            with open(model_path, "w") as f:
                f.write("not a pickle file")

            with pytest.raises(ValueError):
                repo.load_model("bad_model")

    def test_load_model_caching(self):
        """Test that models are cached in memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            # Create and save model
            model = MockModel("churn")
            model_path = Path(tmpdir) / "churn.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            # Load twice
            first_load = repo.load_model("churn")
            second_load = repo.load_model("churn")

            # Should be exact same object (cached)
            assert first_load is second_load

    def test_get_model_from_cache(self):
        """Test getting model from cache without reloading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            # Create and load model
            model = MockModel("churn")
            model_path = Path(tmpdir) / "churn.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            repo.load_model("churn")

            # Get from cache
            cached = repo.get_model("churn")
            assert cached is not None
            assert isinstance(cached, MockModel)

    def test_get_model_not_loaded(self):
        """Test getting model that hasn't been loaded returns None."""
        repo = ModelRepository()
        result = repo.get_model("nonexistent")
        assert result is None


class TestModelRepositoryCaching:
    """Test model caching functionality."""

    def test_list_cached_models(self):
        """Test listing cached models."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            # Create and load multiple models
            for model_name in ["churn", "ltv", "recovery"]:
                model = MockModel(model_name)
                model_path = Path(tmpdir) / f"{model_name}.pkl"
                with open(model_path, "wb") as f:
                    pickle.dump(model, f)
                repo.load_model(model_name)

            # List cached models
            cached = repo.list_cached_models()
            assert len(cached) == 3
            assert "churn:latest" in cached
            assert "ltv:latest" in cached
            assert "recovery:latest" in cached

    def test_cached_model_has_metadata(self):
        """Test cached model includes loading timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            # Create and load model
            model = MockModel("churn")
            model_path = Path(tmpdir) / "churn.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            before = datetime.utcnow()
            repo.load_model("churn")
            after = datetime.utcnow()

            cached = repo.list_cached_models()
            loaded_at = cached["churn:latest"]["loaded_at"]

            assert before <= loaded_at <= after

    def test_clear_cache_all(self):
        """Test clearing all cached models."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            # Create and load models
            for model_name in ["churn", "ltv"]:
                model = MockModel(model_name)
                model_path = Path(tmpdir) / f"{model_name}.pkl"
                with open(model_path, "wb") as f:
                    pickle.dump(model, f)
                repo.load_model(model_name)

            assert len(repo.list_cached_models()) == 2

            # Clear all
            repo.clear_cache()
            assert len(repo.list_cached_models()) == 0

    def test_clear_cache_specific(self):
        """Test clearing specific model from cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            # Create and load models
            for model_name in ["churn", "ltv", "recovery"]:
                model = MockModel(model_name)
                model_path = Path(tmpdir) / f"{model_name}.pkl"
                with open(model_path, "wb") as f:
                    pickle.dump(model, f)
                repo.load_model(model_name)

            assert len(repo.list_cached_models()) == 3

            # Clear only churn
            repo.clear_cache("churn")
            cached = repo.list_cached_models()
            assert len(cached) == 2
            assert "churn:latest" not in cached
            assert "ltv:latest" in cached


class TestModelRepositoryVersioning:
    """Test model versioning support."""

    def test_load_specific_version(self):
        """Test loading specific version of model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            # Create two versions
            for version in ["v1.0", "v1.1"]:
                model = MockModel(f"churn_{version}")
                model_path = Path(tmpdir) / f"churn_{version}.pkl"
                with open(model_path, "wb") as f:
                    pickle.dump(model, f)

            # Load specific version
            v1_0 = repo.load_model("churn", model_version="v1.0")
            v1_1 = repo.load_model("churn", model_version="v1.1")

            assert v1_0.name == "churn_v1.0"
            assert v1_1.name == "churn_v1.1"
            assert v1_0 is not v1_1

    def test_version_caching_separate(self):
        """Test that different versions are cached separately."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            # Create two versions
            for version in ["2024-06-01", "2024-06-10"]:
                model = MockModel(f"churn_{version}")
                model_path = Path(tmpdir) / f"churn_{version}.pkl"
                with open(model_path, "wb") as f:
                    pickle.dump(model, f)

            # Load both versions
            repo.load_model("churn", model_version="2024-06-01")
            repo.load_model("churn", model_version="2024-06-10")

            cached = repo.list_cached_models()
            assert len(cached) == 2
            assert "churn:2024-06-01" in cached
            assert "churn:2024-06-10" in cached


class TestModelRepositoryEdgeCases:
    """Test edge cases and error handling."""

    def test_load_model_logging(self, caplog):
        """Test logging on successful load."""
        import logging
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            # Create model file
            model = MockModel("churn")
            model_path = Path(tmpdir) / "churn.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            with caplog.at_level(logging.INFO):
                repo.load_model("churn")
            assert "Loaded model:" in caplog.text

    def test_cache_hit_logging(self, caplog):
        """Test logging on cache hit."""
        import logging
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            # Create and load model
            model = MockModel("churn")
            model_path = Path(tmpdir) / "churn.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            repo.load_model("churn")
            caplog.clear()

            # Load again
            with caplog.at_level(logging.DEBUG):
                repo.load_model("churn")
            assert "Returning cached model:" in caplog.text

    def test_multiple_model_types(self):
        """Test loading multiple model types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModelRepository(model_dir=tmpdir)

            # Create models for all types
            model_names = ["churn", "ltv", "recovery", "pricing"]
            for name in model_names:
                model = MockModel(name)
                model_path = Path(tmpdir) / f"{name}.pkl"
                with open(model_path, "wb") as f:
                    pickle.dump(model, f)

            # Load all
            for name in model_names:
                loaded = repo.load_model(name)
                assert loaded.name == name

            # All should be cached
            cached = repo.list_cached_models()
            assert len(cached) == len(model_names)
