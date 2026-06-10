"""Multi-level TTL cache with invalidation support.

Features:
- In-memory cache with per-key TTL
- Entity-specific cache methods (products, customers, scores, cohorts)
- Pattern-based invalidation (e.g., "product:*")
- Event-driven invalidation triggers
- Cache metrics (hits, misses)
- Batch operations for efficiency
"""

import logging
import time
from typing import Any, Dict, Optional, List, Set
from datetime import datetime, timezone
from fnmatch import fnmatch
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CacheConfig:
    """Cache configuration."""

    product_ttl: int = 3600  # 1 hour
    customer_ttl: int = 900  # 15 minutes
    score_ttl: int = 86400  # 24 hours
    cohort_ttl: int = 2592000  # 30 days
    collect_metrics: bool = True


@dataclass
class CacheMetrics:
    """Cache metrics."""

    hits: int = 0
    misses: int = 0
    hit_count: int = 0
    miss_count: int = 0
    invalidation_count: int = 0
    last_access_time: Optional[datetime] = None


class Cache:
    """Multi-level TTL cache with entity-specific TTLs and invalidation triggers."""

    def __init__(
        self,
        product_ttl: int = 3600,
        customer_ttl: int = 900,
        score_ttl: int = 86400,
        cohort_ttl: int = 2592000,
        collect_metrics: bool = True,
    ):
        """Initialize cache.

        Args:
            product_ttl: Product cache TTL (seconds, default 1 hour)
            customer_ttl: Customer cache TTL (seconds, default 15 minutes)
            score_ttl: Score cache TTL (seconds, default 24 hours)
            cohort_ttl: Cohort cache TTL (seconds, default 30 days)
            collect_metrics: Enable metrics collection
        """
        self.product_ttl = product_ttl
        self.customer_ttl = customer_ttl
        self.score_ttl = score_ttl
        self.cohort_ttl = cohort_ttl
        self.collect_metrics = collect_metrics

        # Cache storage: key -> (value, ttl, timestamp)
        self._cache: Dict[str, tuple] = {}
        self._metrics = CacheMetrics()

        logger.info(
            "cache_initialized",
            product_ttl=product_ttl,
            customer_ttl=customer_ttl,
            score_ttl=score_ttl,
            cohort_ttl=cohort_ttl,
        )

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a cache value with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (if None, use default from entity type)
        """
        if ttl is None:
            ttl = 3600  # Default 1 hour

        timestamp = time.time()
        self._cache[key] = (value, ttl, timestamp)

        logger.debug("cache_set", key=key, ttl=ttl)

    def get(self, key: str) -> Optional[Any]:
        """Get a cache value, checking TTL expiration.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        if key not in self._cache:
            if self.collect_metrics:
                self._metrics.misses += 1
                self._metrics.miss_count += 1
            logger.debug("cache_miss", key=key)
            return None

        value, ttl, timestamp = self._cache[key]
        age = time.time() - timestamp

        # Check if expired
        if age > ttl:
            del self._cache[key]
            if self.collect_metrics:
                self._metrics.misses += 1
                self._metrics.miss_count += 1
            logger.debug("cache_expired", key=key, age=age, ttl=ttl)
            return None

        if self.collect_metrics:
            self._metrics.hits += 1
            self._metrics.hit_count += 1
            self._metrics.last_access_time = datetime.now(timezone.utc)

        logger.debug("cache_hit", key=key)
        return value

    def invalidate(self, key: str) -> None:
        """Invalidate a specific cache key.

        Args:
            key: Cache key to invalidate
        """
        if key in self._cache:
            del self._cache[key]
            if self.collect_metrics:
                self._metrics.invalidation_count += 1
            logger.debug("cache_invalidated", key=key)

    def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate cache keys matching a pattern (e.g., "product:*").

        Args:
            pattern: Pattern to match (supports fnmatch wildcards)
        """
        keys_to_delete = [
            key for key in self._cache.keys() if fnmatch(key, pattern)
        ]

        for key in keys_to_delete:
            del self._cache[key]
            if self.collect_metrics:
                self._metrics.invalidation_count += 1

        logger.info("cache_pattern_invalidated", pattern=pattern, count=len(keys_to_delete))

    def clear(self) -> None:
        """Clear entire cache."""
        self._cache.clear()
        logger.info("cache_cleared")

    def set_product(self, key: str, value: Any) -> None:
        """Set product cache value with product TTL.

        Args:
            key: Cache key (typically "product:<id>")
            value: Product data
        """
        self.set(key, value, ttl=self.product_ttl)

    def get_product(self, key: str) -> Optional[Any]:
        """Get product cache value.

        Args:
            key: Cache key

        Returns:
            Cached product data or None
        """
        return self.get(key)

    def set_customer(self, key: str, value: Any) -> None:
        """Set customer cache value with customer TTL.

        Args:
            key: Cache key (typically "customer:<id>")
            value: Customer data
        """
        self.set(key, value, ttl=self.customer_ttl)

    def get_customer(self, key: str) -> Optional[Any]:
        """Get customer cache value.

        Args:
            key: Cache key

        Returns:
            Cached customer data or None
        """
        return self.get(key)

    def set_score(self, key: str, value: Any) -> None:
        """Set score cache value with score TTL (churn/LTV/cart).

        Args:
            key: Cache key (typically "churn:<id>" or "ltv:<id>")
            value: Score data
        """
        self.set(key, value, ttl=self.score_ttl)

    def get_score(self, key: str) -> Optional[Any]:
        """Get score cache value.

        Args:
            key: Cache key

        Returns:
            Cached score data or None
        """
        return self.get(key)

    def set_cohort(self, key: str, value: Any) -> None:
        """Set cohort cache value with cohort TTL.

        Args:
            key: Cache key (typically "cohort:<period>")
            value: Cohort data
        """
        self.set(key, value, ttl=self.cohort_ttl)

    def get_cohort(self, key: str) -> Optional[Any]:
        """Get cohort cache value.

        Args:
            key: Cache key

        Returns:
            Cached cohort data or None
        """
        return self.get(key)

    def on_inventory_change(self, product_key: str) -> None:
        """Handle inventory change event - invalidate product cache.

        Args:
            product_key: Product cache key (e.g., "product:123")
        """
        self.invalidate(product_key)
        logger.info("product_cache_invalidated_on_inventory_change", key=product_key)

    def on_customer_update(self, customer_key: str) -> None:
        """Handle customer update event - invalidate customer cache.

        Args:
            customer_key: Customer cache key (e.g., "customer:789")
        """
        self.invalidate(customer_key)
        logger.info("customer_cache_invalidated_on_update", key=customer_key)

    def on_iceberg_refresh(self) -> None:
        """Handle Iceberg refresh event - invalidate cohort cache.

        Iceberg tables (cohort_retention, daily_sales_summary, etc.) are refreshed
        on a schedule (daily/weekly/monthly). When refresh completes, invalidate
        the cohort cache to ensure fresh data is loaded next time.
        """
        self.invalidate_pattern("cohort:*")
        logger.info("cohort_cache_invalidated_on_iceberg_refresh")

    def preload(self, data: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """Preload cache with initial data.

        Args:
            data: Dict of {key: value} to preload
            ttl: TTL for all entries (if None, use 1 hour default)
        """
        if ttl is None:
            ttl = 3600

        for key, value in data.items():
            self.set(key, value, ttl=ttl)

        logger.info("cache_preloaded", count=len(data))

    def batch_set(self, data: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """Batch set multiple cache values.

        Args:
            data: Dict of {key: value} to set
            ttl: TTL for all entries
        """
        self.preload(data, ttl=ttl)

    def batch_invalidate(self, keys: List[str]) -> None:
        """Batch invalidate multiple cache keys.

        Args:
            keys: List of cache keys to invalidate
        """
        for key in keys:
            self.invalidate(key)

        logger.info("cache_batch_invalidated", count=len(keys))

    def size(self) -> int:
        """Get number of items in cache.

        Returns:
            Current cache size
        """
        # Clean up expired entries first
        expired_keys = []
        for key, (value, ttl, timestamp) in self._cache.items():
            if time.time() - timestamp > ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

        return len(self._cache)

    def get_memory_info(self) -> Dict[str, Any]:
        """Get cache memory information.

        Returns:
            Dict with cache size and item count
        """
        return {
            "size": len(self._cache),
            "total_size": len(self._cache),
            "items": len(self._cache),
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics.

        Returns:
            Dict with hits, misses, and other metrics
        """
        return {
            "hits": self._metrics.hits,
            "misses": self._metrics.misses,
            "hit_count": self._metrics.hit_count,
            "miss_count": self._metrics.miss_count,
            "invalidation_count": self._metrics.invalidation_count,
            "last_access_time": self._metrics.last_access_time.isoformat()
            if self._metrics.last_access_time
            else None,
            "cache_size": len(self._cache),
        }

    def reset_metrics(self) -> None:
        """Reset collected metrics."""
        self._metrics = CacheMetrics()
        logger.info("cache_metrics_reset")
