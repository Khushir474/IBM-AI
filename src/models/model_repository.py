"""Model loading and caching for ML inference."""

import logging
import pickle
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ModelRepository:
    """Load and cache ML models for inference."""

    def __init__(self, model_dir: Optional[str] = None):
        """Initialize model repository.

        Args:
            model_dir: Directory containing model files (default: ./models)
        """
        self.model_dir = Path(model_dir or "./models")
        self._models: Dict[str, Dict[str, Any]] = {}
        self._load_timestamps: Dict[str, datetime] = {}

    def load_model(self, model_name: str, model_version: str = "latest") -> Any:
        """Load a model from disk, with caching.

        Args:
            model_name: Name of model (e.g., 'churn', 'ltv', 'recovery', 'pricing')
            model_version: Version identifier (e.g., '2024-06-10', 'v1.2.0', 'latest')

        Returns:
            Loaded model object

        Raises:
            FileNotFoundError: If model file not found
            ValueError: If model file cannot be loaded
        """
        cache_key = f"{model_name}:{model_version}"

        # Return cached model if available
        if cache_key in self._models:
            logger.debug(f"Returning cached model: {cache_key}")
            return self._models[cache_key]["model"]

        # Determine file path
        model_file = self.model_dir / f"{model_name}_{model_version}.pkl"
        if not model_file.exists():
            # Try without version for 'latest'
            if model_version == "latest":
                model_file = self.model_dir / f"{model_name}.pkl"

        if not model_file.exists():
            raise FileNotFoundError(
                f"Model not found: {model_file}. Available models in {self.model_dir}"
            )

        # Load model
        try:
            with open(model_file, "rb") as f:
                model = pickle.load(f)
            logger.info(f"Loaded model: {cache_key} from {model_file}")
        except Exception as e:
            raise ValueError(f"Failed to load model {model_file}: {e}")

        # Cache model with metadata
        self._models[cache_key] = {
            "model": model,
            "path": str(model_file),
            "loaded_at": datetime.utcnow(),
        }
        self._load_timestamps[cache_key] = datetime.utcnow()

        return model

    def get_model(
        self, model_name: str, model_version: str = "latest"
    ) -> Optional[Any]:
        """Get a model without raising if not found.

        Args:
            model_name: Name of model
            model_version: Version identifier

        Returns:
            Model object or None if not found/loaded
        """
        cache_key = f"{model_name}:{model_version}"
        if cache_key in self._models:
            return self._models[cache_key]["model"]
        return None

    def list_cached_models(self) -> Dict[str, Dict[str, Any]]:
        """List all currently cached models with metadata."""
        return {k: {"loaded_at": v["loaded_at"], "path": v["path"]} for k, v in self._models.items()}

    def clear_cache(self, model_name: Optional[str] = None):
        """Clear cached models.

        Args:
            model_name: Specific model to clear, or None to clear all
        """
        if model_name is None:
            self._models.clear()
            self._load_timestamps.clear()
            logger.info("Cleared all cached models")
        else:
            keys_to_remove = [k for k in self._models.keys() if k.startswith(model_name)]
            for key in keys_to_remove:
                del self._models[key]
                if key in self._load_timestamps:
                    del self._load_timestamps[key]
            logger.info(f"Cleared cache for model: {model_name}")
