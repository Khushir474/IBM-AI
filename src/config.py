"""Application configuration management using pydantic-settings.

Loads configuration from environment variables with sensible defaults.
Covers: Cassandra, Presto/Iceberg, Workshop, ML models, caching, feature flags.
"""

from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

import structlog

logger = structlog.get_logger(__name__)


class Settings(BaseSettings):
    """Application configuration loaded from environment variables.

    All settings can be overridden via environment variables using uppercase names.
    Example: api_host -> API_HOST environment variable
    """

    # Application
    app_name: str = Field(default="E-commerce Intelligence Platform")
    app_version: str = Field(default="1.0.0")
    api_prefix: str = Field(default="/api/v1")
    environment: str = Field(default="development")
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_cors_origins: List[str] = Field(default=["http://localhost:3000", "http://localhost:8080"])
    log_level: str = Field(default="INFO")
    use_structlog: bool = Field(default=True)
    debug: bool = Field(default=False)

    # Cassandra
    cassandra_host: str = Field(default="localhost")
    cassandra_port: int = Field(default=9042)
    cassandra_username: str = Field(default="cassandra")
    cassandra_password: str = Field(default="cassandra")
    cassandra_keyspace: str = Field(default="ecommerce")
    cassandra_use_ssl: bool = Field(default=False)
    cassandra_ssl_verify: bool = Field(default=True)
    cassandra_use_route_endpoint_factory: bool = Field(default=False)
    cassandra_connection_timeout: float = Field(default=5.0)
    cassandra_request_timeout: float = Field(default=5.0)
    cassandra_pool_size: int = Field(default=5)
    cassandra_prepared_statement_cache_size: int = Field(default=100)
    cassandra_max_retries: int = Field(default=3)
    cassandra_retry_backoff: float = Field(default=1.0)
    cassandra_retry_jitter: bool = Field(default=True)
    cassandra_collect_metrics: bool = Field(default=True)

    # Presto/Iceberg
    presto_host: str = Field(default="localhost")
    presto_port: int = Field(default=443)
    presto_use_ssl: bool = Field(default=True)
    presto_verify_ssl: bool = Field(default=True)
    presto_query_timeout: float = Field(default=30.0)
    presto_poll_interval: float = Field(default=0.5)
    presto_enable_query_cache: bool = Field(default=True)
    presto_cache_ttl: int = Field(default=86400)
    presto_auto_partition_filter: bool = Field(default=True)
    presto_collect_metrics: bool = Field(default=True)
    presto_timeout: float = Field(default=30.0)

    # Workshop / WXD
    wxd_host: str = Field(default="localhost")
    workshop_user: str = Field(default="user-42")
    workshop_password: str = Field(default="password")
    workshop_schema_suffix: str = Field(default="user_42")
    bearer_token_cache_ttl: int = Field(default=43200)

    # ML Models
    churn_model_enabled: bool = Field(default=True)
    churn_model_endpoint: str = Field(default="http://localhost:5000/churn")
    churn_model_path: Optional[str] = None
    ltv_model_enabled: bool = Field(default=True)
    ltv_model_endpoint: str = Field(default="http://localhost:5000/ltv")
    ltv_model_path: Optional[str] = None
    cart_model_enabled: bool = Field(default=True)
    cart_model_endpoint: str = Field(default="http://localhost:5000/cart")
    recovery_model_path: Optional[str] = None
    pricing_model_enabled: bool = Field(default=True)
    pricing_model_endpoint: str = Field(default="http://localhost:5000/pricing")
    pricing_model_path: Optional[str] = None
    model_inference_timeout: float = Field(default=10.0)

    # Caching
    cache_product_ttl: int = Field(default=3600)
    cache_customer_ttl: int = Field(default=900)
    cache_score_ttl: int = Field(default=86400)
    cache_cohort_ttl: int = Field(default=2592000)
    cache_collect_metrics: bool = Field(default=True)

    # Feature Flags
    feature_churn_prediction: bool = Field(default=True)
    enable_churn_scoring: bool = Field(default=True)
    feature_ltv_prediction: bool = Field(default=True)
    enable_ltv_prediction: bool = Field(default=True)
    feature_cart_recovery: bool = Field(default=True)
    enable_cart_recovery: bool = Field(default=True)
    feature_dynamic_pricing: bool = Field(default=True)
    enable_pricing_optimization: bool = Field(default=True)

    # Retry settings
    max_retries: int = Field(default=3)
    retry_backoff: float = Field(default=1.0)
    retry_jitter: bool = Field(default=True)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("api_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            if v.startswith("["):
                # Already a JSON list string, let Pydantic handle it
                import json
                try:
                    return json.loads(v)
                except:
                    pass
            return [origin.strip() for origin in v.split(",")]
        if isinstance(v, list):
            return v
        return v

    def __init__(self, **data):
        """Initialize settings and log configuration."""
        super().__init__(**data)

        logger.info(
            "settings_loaded",
            environment=self.environment,
            cassandra_host=self.cassandra_host,
            presto_host=self.presto_host,
            wxd_host=self.wxd_host,
            log_level=self.log_level,
        )


    def get_cassandra_config(self) -> dict:
        """Get Cassandra client configuration.

        Returns:
            Dict with Cassandra client parameters
        """
        return {
            "host": self.cassandra_host,
            "port": self.cassandra_port,
            "username": self.cassandra_username,
            "password": self.cassandra_password,
            "keyspace": self.cassandra_keyspace,
            "use_ssl": self.cassandra_use_ssl,
            "ssl_verify": self.cassandra_ssl_verify,
            "use_route_endpoint_factory": self.cassandra_use_route_endpoint_factory,
            "connection_timeout": self.cassandra_connection_timeout,
            "request_timeout": self.cassandra_request_timeout,
            "pool_size": self.cassandra_pool_size,
            "prepared_statement_cache_size": self.cassandra_prepared_statement_cache_size,
            "max_retries": self.cassandra_max_retries,
            "retry_backoff": self.cassandra_retry_backoff,
            "retry_jitter": self.cassandra_retry_jitter,
            "collect_metrics": self.cassandra_collect_metrics,
        }

    def get_presto_config(self) -> dict:
        """Get Presto client configuration.

        Returns:
            Dict with Presto client parameters
        """
        return {
            "presto_host": self.presto_host,
            "presto_port": self.presto_port,
            "wxd_host": self.wxd_host,
            "workshop_user": self.workshop_user,
            "workshop_password": self.workshop_password,
            "use_ssl": self.presto_use_ssl,
            "verify_ssl": self.presto_verify_ssl,
            "query_timeout": self.presto_query_timeout,
            "poll_interval": self.presto_poll_interval,
            "token_cache_ttl": self.bearer_token_cache_ttl,
            "enable_query_cache": self.presto_enable_query_cache,
            "cache_ttl": self.presto_cache_ttl,
            "auto_partition_filter": self.presto_auto_partition_filter,
            "collect_metrics": self.presto_collect_metrics,
        }

    def get_cache_config(self) -> dict:
        """Get cache configuration.

        Returns:
            Dict with cache parameters
        """
        return {
            "product_ttl": self.cache_product_ttl,
            "customer_ttl": self.cache_customer_ttl,
            "score_ttl": self.cache_score_ttl,
            "cohort_ttl": self.cache_cohort_ttl,
            "collect_metrics": self.cache_collect_metrics,
        }

    def get_ml_models_config(self) -> dict:
        """Get ML models configuration.

        Returns:
            Dict with model endpoints and settings
        """
        return {
            "churn_prediction": {
                "enabled": self.churn_model_enabled,
                "endpoint": self.churn_model_endpoint,
                "timeout": self.model_inference_timeout,
            },
            "ltv_prediction": {
                "enabled": self.ltv_model_enabled,
                "endpoint": self.ltv_model_endpoint,
                "timeout": self.model_inference_timeout,
            },
            "cart_abandonment": {
                "enabled": self.cart_model_enabled,
                "endpoint": self.cart_model_endpoint,
                "timeout": self.model_inference_timeout,
            },
            "dynamic_pricing": {
                "enabled": self.pricing_model_enabled,
                "endpoint": self.pricing_model_endpoint,
                "timeout": self.model_inference_timeout,
            },
        }

    def get_feature_flags(self) -> dict:
        """Get feature flags.

        Returns:
            Dict with feature flag states
        """
        return {
            "churn_prediction": self.feature_churn_prediction,
            "ltv_prediction": self.feature_ltv_prediction,
            "cart_recovery": self.feature_cart_recovery,
            "dynamic_pricing": self.feature_dynamic_pricing,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance (singleton pattern)."""
    return Settings()
