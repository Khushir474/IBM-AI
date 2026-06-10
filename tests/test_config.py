"""Tests for Task 0.5: Configuration & Environment Management."""

import os
import pytest
from pathlib import Path


class TestConfigImports:
    """Verify config module can be imported."""

    def test_config_module_importable(self):
        """Test that config module can be imported."""
        try:
            from src.config import Settings
            assert Settings is not None
        except ImportError as e:
            pytest.fail(f"Failed to import config module: {e}")


class TestConfigInitialization:
    """Test configuration initialization from environment."""

    def test_settings_initialization(self):
        """Test that Settings can be initialized."""
        from src.config import Settings

        settings = Settings()
        assert settings is not None

    def test_settings_from_env(self, monkeypatch):
        """Test loading settings from environment variables."""
        from src.config import Settings

        # Set required env vars
        monkeypatch.setenv("CASSANDRA_HOST", "cassandra.example.com")
        monkeypatch.setenv("CASSANDRA_PORT", "9042")
        monkeypatch.setenv("PRESTO_HOST", "presto.example.com")
        monkeypatch.setenv("WXD_HOST", "software-hub.example.com")
        monkeypatch.setenv("WORKSHOP_USER", "user-42")
        monkeypatch.setenv("WORKSHOP_PASSWORD", "secret")

        settings = Settings()
        assert settings.cassandra_host == "cassandra.example.com"
        assert settings.cassandra_port == 9042
        assert settings.presto_host == "presto.example.com"


class TestCassandraSettings:
    """Test Cassandra-specific configuration."""

    def test_cassandra_default_values(self):
        """Test Cassandra default configuration values."""
        from src.config import Settings

        settings = Settings()

        # Port comes from conftest.py env (9042)
        assert settings.cassandra_port == 9042
        # use_ssl is configured as False in the default, but can be overridden
        assert isinstance(settings.cassandra_use_ssl, bool)
        assert settings.cassandra_connection_timeout > 0
        assert settings.cassandra_request_timeout > 0

    def test_cassandra_ssl_configuration(self, monkeypatch):
        """Test Cassandra SSL/TLS configuration."""
        from src.config import Settings

        monkeypatch.setenv("CASSANDRA_HOST", "cassandra.example.com")
        monkeypatch.setenv("CASSANDRA_PORT", "443")
        monkeypatch.setenv("CASSANDRA_USE_SSL", "true")
        monkeypatch.setenv("CASSANDRA_SSL_VERIFY", "true")

        settings = Settings()
        assert settings.cassandra_port == 443
        assert settings.cassandra_use_ssl is True
        assert settings.cassandra_ssl_verify is True

    def test_cassandra_route_endpoint_factory(self, monkeypatch):
        """Test Cassandra Route endpoint factory configuration."""
        from src.config import Settings

        monkeypatch.setenv("CASSANDRA_HOST", "cassandra.apps.example.com")
        monkeypatch.setenv("CASSANDRA_USE_ROUTE_ENDPOINT_FACTORY", "true")

        settings = Settings()
        assert settings.cassandra_use_route_endpoint_factory is True

    def test_cassandra_connection_timeouts(self, monkeypatch):
        """Test Cassandra timeout configuration."""
        from src.config import Settings

        monkeypatch.setenv("CASSANDRA_CONNECTION_TIMEOUT", "10.0")
        monkeypatch.setenv("CASSANDRA_REQUEST_TIMEOUT", "5.0")

        settings = Settings()
        assert settings.cassandra_connection_timeout == 10.0
        assert settings.cassandra_request_timeout == 5.0

    def test_cassandra_pool_size(self, monkeypatch):
        """Test Cassandra connection pool configuration."""
        from src.config import Settings

        monkeypatch.setenv("CASSANDRA_POOL_SIZE", "20")

        settings = Settings()
        assert settings.cassandra_pool_size == 20

    def test_cassandra_retry_configuration(self, monkeypatch):
        """Test Cassandra retry logic configuration."""
        from src.config import Settings

        monkeypatch.setenv("CASSANDRA_MAX_RETRIES", "5")
        monkeypatch.setenv("CASSANDRA_RETRY_BACKOFF", "2.0")
        monkeypatch.setenv("CASSANDRA_RETRY_JITTER", "true")

        settings = Settings()
        assert settings.cassandra_max_retries == 5
        assert settings.cassandra_retry_backoff == 2.0
        assert settings.cassandra_retry_jitter is True


class TestPrestoSettings:
    """Test Presto/Iceberg-specific configuration."""

    def test_presto_default_values(self):
        """Test Presto default configuration values."""
        from src.config import Settings

        settings = Settings()

        # Port comes from conftest.py env (8080), not the default
        assert settings.presto_port == 8080
        assert settings.presto_use_ssl is True
        assert settings.presto_query_timeout > 0
        assert settings.presto_poll_interval > 0

    def test_presto_query_timeout(self, monkeypatch):
        """Test Presto query timeout configuration."""
        from src.config import Settings

        monkeypatch.setenv("PRESTO_QUERY_TIMEOUT", "60.0")

        settings = Settings()
        assert settings.presto_query_timeout == 60.0

    def test_presto_polling_configuration(self, monkeypatch):
        """Test Presto query polling configuration."""
        from src.config import Settings

        monkeypatch.setenv("PRESTO_POLL_INTERVAL", "1.0")

        settings = Settings()
        assert settings.presto_poll_interval == 1.0

    def test_presto_cache_configuration(self, monkeypatch):
        """Test Presto query cache configuration."""
        from src.config import Settings

        monkeypatch.setenv("PRESTO_ENABLE_QUERY_CACHE", "true")
        monkeypatch.setenv("PRESTO_CACHE_TTL", "86400")

        settings = Settings()
        assert settings.presto_enable_query_cache is True
        assert settings.presto_cache_ttl == 86400

    def test_presto_partition_filtering(self, monkeypatch):
        """Test Presto partition filtering configuration."""
        from src.config import Settings

        monkeypatch.setenv("PRESTO_AUTO_PARTITION_FILTER", "true")

        settings = Settings()
        assert settings.presto_auto_partition_filter is True


class TestWorkshopSettings:
    """Test Workshop/WXD environment configuration."""

    def test_workshop_required_settings(self):
        """Test that workshop settings are available."""
        from src.config import Settings

        settings = Settings()

        # Should have workshop user/password attributes
        assert hasattr(settings, "workshop_user")
        assert hasattr(settings, "workshop_password")

    def test_workshop_schema_configuration(self, monkeypatch):
        """Test Workshop schema configuration."""
        from src.config import Settings

        monkeypatch.setenv("WORKSHOP_SCHEMA_SUFFIX", "user_42")

        settings = Settings()
        assert settings.workshop_schema_suffix == "user_42"

    def test_wxd_host_configuration(self, monkeypatch):
        """Test Software Hub (WXD) host configuration."""
        from src.config import Settings

        monkeypatch.setenv("WXD_HOST", "software-hub.example.com")

        settings = Settings()
        assert settings.wxd_host == "software-hub.example.com"

    def test_bearer_token_cache_ttl(self, monkeypatch):
        """Test bearer token cache TTL configuration."""
        from src.config import Settings

        monkeypatch.setenv("BEARER_TOKEN_CACHE_TTL", "43200")

        settings = Settings()
        assert settings.bearer_token_cache_ttl == 43200


class TestMLModelSettings:
    """Test ML model-specific configuration."""

    def test_churn_model_configuration(self, monkeypatch):
        """Test churn prediction model configuration."""
        from src.config import Settings

        monkeypatch.setenv("CHURN_MODEL_ENDPOINT", "http://ml-service:5000/churn")
        monkeypatch.setenv("CHURN_MODEL_ENABLED", "true")

        settings = Settings()
        assert settings.churn_model_enabled is True
        assert settings.churn_model_endpoint == "http://ml-service:5000/churn"

    def test_ltv_model_configuration(self, monkeypatch):
        """Test LTV prediction model configuration."""
        from src.config import Settings

        monkeypatch.setenv("LTV_MODEL_ENDPOINT", "http://ml-service:5000/ltv")
        monkeypatch.setenv("LTV_MODEL_ENABLED", "true")

        settings = Settings()
        assert settings.ltv_model_enabled is True
        assert settings.ltv_model_endpoint == "http://ml-service:5000/ltv"

    def test_cart_abandonment_model_configuration(self, monkeypatch):
        """Test cart abandonment recovery model configuration."""
        from src.config import Settings

        monkeypatch.setenv("CART_MODEL_ENDPOINT", "http://ml-service:5000/cart")
        monkeypatch.setenv("CART_MODEL_ENABLED", "true")

        settings = Settings()
        assert settings.cart_model_enabled is True
        assert settings.cart_model_endpoint == "http://ml-service:5000/cart"

    def test_pricing_model_configuration(self, monkeypatch):
        """Test dynamic pricing model configuration."""
        from src.config import Settings

        monkeypatch.setenv("PRICING_MODEL_ENDPOINT", "http://ml-service:5000/pricing")
        monkeypatch.setenv("PRICING_MODEL_ENABLED", "true")

        settings = Settings()
        assert settings.pricing_model_enabled is True
        assert settings.pricing_model_endpoint == "http://ml-service:5000/pricing"

    def test_model_inference_timeout(self, monkeypatch):
        """Test model inference timeout configuration."""
        from src.config import Settings

        monkeypatch.setenv("MODEL_INFERENCE_TIMEOUT", "30.0")

        settings = Settings()
        assert settings.model_inference_timeout == 30.0


class TestCacheSettings:
    """Test cache configuration."""

    def test_cache_ttl_configuration(self, monkeypatch):
        """Test cache TTL configuration."""
        from src.config import Settings

        monkeypatch.setenv("CACHE_PRODUCT_TTL", "7200")
        monkeypatch.setenv("CACHE_CUSTOMER_TTL", "1800")
        monkeypatch.setenv("CACHE_SCORE_TTL", "86400")
        monkeypatch.setenv("CACHE_COHORT_TTL", "2592000")

        settings = Settings()
        assert settings.cache_product_ttl == 7200
        assert settings.cache_customer_ttl == 1800
        assert settings.cache_score_ttl == 86400
        assert settings.cache_cohort_ttl == 2592000

    def test_cache_metrics_enabled(self, monkeypatch):
        """Test cache metrics configuration."""
        from src.config import Settings

        monkeypatch.setenv("CACHE_COLLECT_METRICS", "true")

        settings = Settings()
        assert settings.cache_collect_metrics is True


class TestFeatureFlags:
    """Test feature flag configuration."""

    def test_feature_flags(self, monkeypatch):
        """Test feature flag configuration."""
        from src.config import Settings

        monkeypatch.setenv("FEATURE_CHURN_PREDICTION", "true")
        monkeypatch.setenv("FEATURE_LTV_PREDICTION", "true")
        monkeypatch.setenv("FEATURE_CART_RECOVERY", "true")
        monkeypatch.setenv("FEATURE_DYNAMIC_PRICING", "true")

        settings = Settings()
        assert settings.feature_churn_prediction is True
        assert settings.feature_ltv_prediction is True
        assert settings.feature_cart_recovery is True
        assert settings.feature_dynamic_pricing is True

    def test_feature_flags_defaults(self):
        """Test feature flag default values."""
        from src.config import Settings

        settings = Settings()

        # Defaults should be available
        assert hasattr(settings, "feature_churn_prediction")
        assert hasattr(settings, "feature_ltv_prediction")
        assert hasattr(settings, "feature_cart_recovery")
        assert hasattr(settings, "feature_dynamic_pricing")


class TestLoggingConfiguration:
    """Test logging configuration."""

    def test_log_level_configuration(self, monkeypatch):
        """Test logging level configuration."""
        from src.config import Settings

        monkeypatch.setenv("LOG_LEVEL", "DEBUG")

        settings = Settings()
        assert settings.log_level == "DEBUG"

    def test_structlog_enabled(self, monkeypatch):
        """Test structured logging configuration."""
        from src.config import Settings

        monkeypatch.setenv("USE_STRUCTLOG", "true")

        settings = Settings()
        assert settings.use_structlog is True


class TestAPIConfiguration:
    """Test API server configuration."""

    def test_api_host_port(self, monkeypatch):
        """Test API server host/port configuration."""
        from src.config import Settings

        monkeypatch.setenv("API_HOST", "0.0.0.0")
        monkeypatch.setenv("API_PORT", "8000")

        settings = Settings()
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000

    def test_api_cors_origins(self):
        """Test API CORS origins configuration."""
        from src.config import Settings

        settings = Settings()
        # Should be a list of origins
        assert isinstance(settings.api_cors_origins, list)
        assert len(settings.api_cors_origins) > 0


class TestConfigValidation:
    """Test configuration validation."""

    def test_config_validation_errors(self, monkeypatch):
        """Test that invalid configuration raises errors."""
        from src.config import Settings
        from pydantic import ValidationError

        # Set invalid port
        monkeypatch.setenv("CASSANDRA_PORT", "invalid_port")

        with pytest.raises((ValidationError, ValueError)):
            Settings()

    def test_config_type_coercion(self, monkeypatch):
        """Test that configuration values are properly coerced to types."""
        from src.config import Settings

        monkeypatch.setenv("CASSANDRA_PORT", "9042")
        monkeypatch.setenv("API_PORT", "8000")

        settings = Settings()
        assert isinstance(settings.cassandra_port, int)
        assert isinstance(settings.api_port, int)

    def test_bool_configuration(self, monkeypatch):
        """Test boolean configuration parsing."""
        from src.config import Settings

        monkeypatch.setenv("CASSANDRA_USE_SSL", "true")
        monkeypatch.setenv("CASSANDRA_SSL_VERIFY", "false")

        settings = Settings()
        assert settings.cassandra_use_ssl is True
        assert settings.cassandra_ssl_verify is False


class TestConfigurationProfiles:
    """Test different configuration profiles."""

    def test_dev_profile(self, monkeypatch):
        """Test development profile configuration."""
        from src.config import Settings

        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")

        settings = Settings()
        assert settings.environment == "development"
        assert settings.log_level == "DEBUG"

    def test_prod_profile(self, monkeypatch):
        """Test production profile configuration."""
        from src.config import Settings

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("LOG_LEVEL", "INFO")

        settings = Settings()
        assert settings.environment == "production"
        assert settings.log_level == "INFO"


class TestSettingsAccess:
    """Test accessing configuration in different ways."""

    def test_settings_as_dict(self):
        """Test accessing settings as dictionary."""
        from src.config import Settings

        settings = Settings()
        settings_dict = settings.model_dump()

        assert isinstance(settings_dict, dict)
        assert "cassandra_host" in settings_dict or "cassandra_port" in settings_dict

    def test_settings_env_vars(self):
        """Test that settings respect environment variables."""
        from src.config import Settings

        # Settings should be populated from env (from conftest.py)
        settings = Settings()
        assert hasattr(settings, "cassandra_host")
        assert hasattr(settings, "presto_host")
        assert hasattr(settings, "workshop_user")


class TestDatabaseSettings:
    """Test database-specific settings."""

    def test_keyspace_configuration(self, monkeypatch):
        """Test Cassandra keyspace configuration."""
        from src.config import Settings

        monkeypatch.setenv("CASSANDRA_KEYSPACE", "ecommerce_user_42")

        settings = Settings()
        assert settings.cassandra_keyspace == "ecommerce_user_42"

    def test_prepared_statement_cache(self, monkeypatch):
        """Test prepared statement cache size configuration."""
        from src.config import Settings

        monkeypatch.setenv("CASSANDRA_PREPARED_STATEMENT_CACHE_SIZE", "200")

        settings = Settings()
        assert settings.cassandra_prepared_statement_cache_size == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
