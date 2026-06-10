"""Application configuration management using pydantic-settings."""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration loaded from environment or .env file."""

    # FastAPI settings
    app_name: str = "E-commerce Intelligence Platform"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    debug: bool = False
    environment: str = "development"

    # Cassandra settings
    cassandra_host: str
    cassandra_port: int = 443
    cassandra_use_ssl: bool = True
    cassandra_user: str = "cassandra"
    cassandra_password: str = "cassandra"
    cassandra_keyspace: str = "ecommerce"
    cassandra_connection_timeout: float = 5.0
    cassandra_request_timeout: float = 5.0

    # Presto/Iceberg settings
    wxd_host: str
    presto_host: str
    presto_port: int = 443
    presto_timeout: float = 30.0
    presto_use_ssl: bool = True

    # Workshop authentication
    workshop_user: str
    workshop_password: str
    workshop_schema_suffix: str

    # ML model paths
    churn_model_path: Optional[str] = None
    ltv_model_path: Optional[str] = None
    recovery_model_path: Optional[str] = None
    pricing_model_path: Optional[str] = None

    # Cache settings (TTL in seconds)
    cache_product_ttl: int = 3600  # 1 hour
    cache_customer_ttl: int = 900  # 15 minutes
    cache_score_ttl: int = 86400  # 24 hours
    cache_cohort_ttl: int = 2592000  # 30 days

    # Feature flags
    enable_churn_scoring: bool = True
    enable_ltv_prediction: bool = True
    enable_cart_recovery: bool = True
    enable_pricing_optimization: bool = True

    # Retry settings
    max_retries: int = 3
    retry_backoff: float = 1.0
    retry_jitter: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance (singleton pattern)."""
    return Settings()
