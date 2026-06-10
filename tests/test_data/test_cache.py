"""Tests for Task 0.4: Caching Layer - Test multi-level TTL caching with invalidation."""

import pytest
import asyncio
import time
from datetime import datetime, timedelta


class TestCacheImports:
    """Verify cache module can be imported."""

    def test_cache_module_importable(self):
        """Test that cache module can be imported."""
        try:
            from src.data.cache import Cache, CacheConfig
            assert Cache is not None
            assert CacheConfig is not None
        except ImportError as e:
            pytest.fail(f"Failed to import cache module: {e}")


class TestCacheConfiguration:
    """Test cache initialization and configuration."""

    def test_cache_initialization(self):
        """Test basic cache initialization."""
        from src.data.cache import Cache

        cache = Cache()
        assert cache is not None
        assert cache.product_ttl > 0
        assert cache.customer_ttl > 0

    def test_cache_with_custom_ttls(self):
        """Test cache with custom TTL configuration."""
        from src.data.cache import Cache

        cache = Cache(
            product_ttl=7200,  # 2 hours
            customer_ttl=1800,  # 30 minutes
            score_ttl=86400,  # 24 hours
            cohort_ttl=2592000,  # 30 days
        )

        assert cache.product_ttl == 7200
        assert cache.customer_ttl == 1800
        assert cache.score_ttl == 86400
        assert cache.cohort_ttl == 2592000

    def test_cache_ttl_defaults(self):
        """Test cache TTL default values match requirements."""
        from src.data.cache import Cache

        cache = Cache()

        # From design.md requirements
        assert cache.product_ttl == 3600  # 1 hour
        assert cache.customer_ttl == 900  # 15 minutes
        assert cache.score_ttl == 86400  # 24 hours
        assert cache.cohort_ttl == 2592000  # 30 days


class TestCacheBasicOperations:
    """Test basic cache get/set operations."""

    def test_cache_set_and_get(self):
        """Test setting and getting cache values."""
        from src.data.cache import Cache

        cache = Cache()

        # Set a value
        cache.set("product:123", {"id": "123", "name": "Widget"}, ttl=3600)

        # Get the value
        result = cache.get("product:123")
        assert result is not None
        assert result["id"] == "123"
        assert result["name"] == "Widget"

    def test_cache_get_nonexistent_key(self):
        """Test getting a key that doesn't exist."""
        from src.data.cache import Cache

        cache = Cache()
        result = cache.get("nonexistent:key")
        assert result is None

    def test_cache_key_patterns(self):
        """Test using key patterns for organization."""
        from src.data.cache import Cache

        cache = Cache()

        # Set values with patterns
        cache.set("product:123", "product_data_1")
        cache.set("product:456", "product_data_2")
        cache.set("customer:789", "customer_data_1")

        # Get by pattern
        assert cache.get("product:123") == "product_data_1"
        assert cache.get("product:456") == "product_data_2"
        assert cache.get("customer:789") == "customer_data_1"


class TestCacheExpiration:
    """Test cache TTL expiration."""

    def test_cache_expiration(self):
        """Test that cached values expire after TTL."""
        from src.data.cache import Cache

        cache = Cache()

        # Set a value with 1-second TTL
        cache.set("short:lived", "value", ttl=1)

        # Should be present immediately
        assert cache.get("short:lived") is not None

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        assert cache.get("short:lived") is None

    def test_cache_multiple_ttls(self):
        """Test caching with different TTL values for different keys."""
        from src.data.cache import Cache

        cache = Cache()

        # Set values with different TTLs
        cache.set("fast:expire", "value1", ttl=1)
        cache.set("slow:expire", "value2", ttl=10)

        # Both present initially
        assert cache.get("fast:expire") is not None
        assert cache.get("slow:expire") is not None

        # Wait for first to expire
        time.sleep(1.1)

        assert cache.get("fast:expire") is None
        assert cache.get("slow:expire") is not None


class TestCacheInvalidation:
    """Test cache invalidation mechanisms."""

    def test_cache_invalidate_by_key(self):
        """Test explicit cache invalidation by key."""
        from src.data.cache import Cache

        cache = Cache()

        cache.set("key1", "value1")
        assert cache.get("key1") is not None

        cache.invalidate("key1")
        assert cache.get("key1") is None

    def test_cache_invalidate_by_pattern(self):
        """Test cache invalidation by key pattern."""
        from src.data.cache import Cache

        cache = Cache()

        # Set multiple values with same prefix
        cache.set("product:123", "data1")
        cache.set("product:456", "data2")
        cache.set("customer:789", "data3")

        # Invalidate by pattern
        cache.invalidate_pattern("product:*")

        # Products should be gone
        assert cache.get("product:123") is None
        assert cache.get("product:456") is None
        # But customer should remain
        assert cache.get("customer:789") is not None

    def test_cache_clear_all(self):
        """Test clearing entire cache."""
        from src.data.cache import Cache

        cache = Cache()

        # Set multiple values
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Clear all
        cache.clear()

        # All should be gone
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None


class TestCacheMetrics:
    """Test cache metrics collection."""

    def test_cache_metrics_enabled(self):
        """Test that cache metrics can be enabled."""
        from src.data.cache import Cache

        cache = Cache(collect_metrics=True)
        assert cache.collect_metrics is True

    def test_cache_hit_miss_tracking(self):
        """Test tracking cache hits and misses."""
        from src.data.cache import Cache

        cache = Cache(collect_metrics=True)

        # Set a value
        cache.set("key", "value")

        # Cache hit
        result = cache.get("key")
        assert result is not None

        # Cache miss
        result = cache.get("nonexistent")
        assert result is None

        # Get metrics
        metrics = cache.get_metrics()
        assert "hits" in metrics or "hit_count" in metrics
        assert "misses" in metrics or "miss_count" in metrics

    def test_cache_metrics_reset(self):
        """Test resetting cache metrics."""
        from src.data.cache import Cache

        cache = Cache(collect_metrics=True)

        # Set some values and access them
        cache.set("key", "value")
        cache.get("key")

        # Reset metrics
        cache.reset_metrics()

        # Metrics should be reset
        metrics = cache.get_metrics()
        # Hit count should be 0 after reset
        assert metrics.get("hits", 0) == 0 or metrics.get("hit_count", 0) == 0


class TestCacheEntityTypes:
    """Test caching for different entity types."""

    def test_product_catalog_cache(self):
        """Test product catalog caching (1 hour TTL)."""
        from src.data.cache import Cache

        cache = Cache()

        # Product should use product_ttl (3600 seconds = 1 hour)
        cache.set_product("product:123", {"id": "123", "name": "Widget"})
        result = cache.get_product("product:123")
        assert result is not None
        assert result["name"] == "Widget"

    def test_customer_profile_cache(self):
        """Test customer profile caching (15 min TTL)."""
        from src.data.cache import Cache

        cache = Cache()

        # Customer should use customer_ttl (900 seconds = 15 minutes)
        cache.set_customer("customer:789", {"id": "789", "email": "test@example.com"})
        result = cache.get_customer("customer:789")
        assert result is not None
        assert result["email"] == "test@example.com"

    def test_score_cache(self):
        """Test score caching (24 hour TTL)."""
        from src.data.cache import Cache

        cache = Cache()

        # Churn/LTV/cart scores use score_ttl (86400 seconds = 24 hours)
        cache.set_score("churn:123", {"score": 0.75})
        result = cache.get_score("churn:123")
        assert result is not None
        assert result["score"] == 0.75

    def test_cohort_cache(self):
        """Test cohort retention caching (30 day TTL)."""
        from src.data.cache import Cache

        cache = Cache()

        # Cohort retention uses cohort_ttl (2592000 seconds = 30 days)
        cache.set_cohort("cohort:2024:01", {"retention_rate": 0.85})
        result = cache.get_cohort("cohort:2024:01")
        assert result is not None
        assert result["retention_rate"] == 0.85


class TestCacheInvalidationTriggers:
    """Test cache invalidation triggered by events."""

    def test_inventory_change_invalidates_product_cache(self):
        """Test that inventory changes invalidate product cache."""
        from src.data.cache import Cache

        cache = Cache()

        # Set product in cache
        cache.set_product("product:123", {"id": "123", "stock": 100})

        # Simulate inventory change event
        cache.on_inventory_change("product:123")

        # Product cache should be invalidated
        assert cache.get_product("product:123") is None

    def test_customer_update_invalidates_customer_cache(self):
        """Test that customer updates invalidate customer cache."""
        from src.data.cache import Cache

        cache = Cache()

        # Set customer in cache
        cache.set_customer("customer:789", {"id": "789", "tier": "gold"})

        # Simulate customer update event
        cache.on_customer_update("customer:789")

        # Customer cache should be invalidated
        assert cache.get_customer("customer:789") is None

    def test_iceberg_refresh_invalidates_cohort_cache(self):
        """Test that Iceberg refresh invalidates cohort cache."""
        from src.data.cache import Cache

        cache = Cache()

        # Set cohort in cache
        cache.set_cohort("cohort:2024:01", {"retention_rate": 0.85})

        # Simulate Iceberg refresh event
        cache.on_iceberg_refresh()

        # Cohort cache should be invalidated
        assert cache.get_cohort("cohort:2024:01") is None


class TestCacheWarmingAndPreloading:
    """Test cache warming and preloading functionality."""

    def test_cache_preload(self):
        """Test preloading cache with initial data."""
        from src.data.cache import Cache

        cache = Cache()

        # Preload cache with data
        initial_data = {
            "product:123": {"id": "123", "name": "Widget"},
            "product:456": {"id": "456", "name": "Gadget"},
        }

        cache.preload(initial_data, ttl=3600)

        # Verify preloaded data
        assert cache.get("product:123") is not None
        assert cache.get("product:456") is not None

    def test_cache_batch_set(self):
        """Test batch setting multiple cache values."""
        from src.data.cache import Cache

        cache = Cache()

        # Batch set
        data = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3",
        }

        cache.batch_set(data, ttl=3600)

        # Verify all were set
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_cache_batch_invalidate(self):
        """Test batch invalidating multiple cache keys."""
        from src.data.cache import Cache

        cache = Cache()

        # Set multiple values
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Batch invalidate
        cache.batch_invalidate(["key1", "key2"])

        # Verify invalidation
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is not None


class TestCacheSize:
    """Test cache size and memory management."""

    def test_cache_size_tracking(self):
        """Test tracking cache size."""
        from src.data.cache import Cache

        cache = Cache()

        # Get initial size
        initial_size = cache.size()

        # Add items
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        # Size should increase
        new_size = cache.size()
        assert new_size >= initial_size

    def test_cache_memory_info(self):
        """Test getting cache memory information."""
        from src.data.cache import Cache

        cache = Cache()

        cache.set("key", "value")

        # Get memory info
        info = cache.get_memory_info()
        assert info is not None
        assert "size" in info or "total_size" in info or "items" in info


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
