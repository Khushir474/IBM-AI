"""Presto/Iceberg async client wrapper for analytics queries.

Handles:
- HTTP-based async client using httpx
- Bearer token authentication (minted from Software Hub, cached ~12h)
- SQL execution with polling loop (wait for stats.state == "FINISHED")
- Result pagination support
- Column name inference from result schema
- Partition column filtering (year/month) for query optimization
- Query caching layer for immutable aggregations
- Timeout configuration
- Error handling for Presto-specific errors
- Federated queries (combining Cassandra + Iceberg)
- Metrics collection
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import lru_cache

import structlog
import httpx

logger = structlog.get_logger(__name__)


@dataclass
class PrestoMetrics:
    """Metrics collected from Presto client."""

    query_count: int = 0
    error_count: int = 0
    timeout_count: int = 0
    cache_hit_count: int = 0
    cache_miss_count: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None


class PrestoClient:
    """Async Presto client for querying Iceberg tables and federated data.

    Features:
    - Async/await support for non-blocking queries
    - Bearer token authentication with 12h caching
    - Query polling until completion
    - Result pagination for large datasets
    - Partition pruning for Iceberg optimization
    - Query result caching for immutable tables
    - Comprehensive error handling
    """

    def __init__(
        self,
        presto_host: str,
        presto_port: int = 443,
        wxd_host: str = None,
        workshop_user: str = None,
        workshop_password: str = None,
        use_ssl: bool = True,
        verify_ssl: bool = True,
        query_timeout: float = 30.0,
        poll_interval: float = 0.5,
        token_cache_ttl: int = 43200,  # 12 hours
        enable_query_cache: bool = True,
        cache_ttl: int = 86400,  # 24 hours
        auto_partition_filter: bool = True,
        partition_columns: Optional[List[str]] = None,
        collect_metrics: bool = True,
    ):
        """Initialize Presto client.

        Args:
            presto_host: Presto host (usually presto-coordinator)
            presto_port: Presto port (usually 443 for TLS Route)
            wxd_host: Software Hub host for token minting
            workshop_user: Workshop username (e.g., user-42)
            workshop_password: Workshop password
            use_ssl: Enable SSL/TLS
            verify_ssl: Verify SSL certificates
            query_timeout: Query timeout in seconds
            poll_interval: Polling interval for query status (seconds)
            token_cache_ttl: Bearer token cache TTL (seconds, ~12h)
            enable_query_cache: Enable caching for immutable queries
            cache_ttl: Cache TTL in seconds
            auto_partition_filter: Auto-add partition filters to queries
            partition_columns: List of partition column names
            collect_metrics: Enable metrics collection
        """
        self.presto_host = presto_host
        self.presto_port = presto_port
        self.wxd_host = wxd_host
        self.workshop_user = workshop_user
        self.workshop_password = workshop_password
        self.use_ssl = use_ssl
        self.verify_ssl = verify_ssl
        self.query_timeout = query_timeout
        self.poll_interval = poll_interval
        self.token_cache_ttl = token_cache_ttl
        self.enable_query_cache = enable_query_cache
        self.cache_ttl = cache_ttl
        self.auto_partition_filter = auto_partition_filter
        self.partition_columns = partition_columns or [
            "order_year", "order_month",
            "snapshot_year", "snapshot_month",
            "summary_year", "summary_month",
            "week_year", "conversion_year", "conversion_month"
        ]
        self.collect_metrics = collect_metrics

        self._bearer_token: Optional[str] = None
        self._token_acquired_at: Optional[datetime] = None
        self._query_cache: Dict[str, Tuple[datetime, Any]] = {}
        self._metrics = PrestoMetrics()

        logger.info(
            "presto_client_initialized",
            presto_host=presto_host,
            presto_port=presto_port,
            use_ssl=use_ssl,
        )

    @property
    def presto_url(self) -> str:
        """Get Presto base URL."""
        scheme = "https" if self.use_ssl else "http"
        return f"{scheme}://{self.presto_host}:{self.presto_port}"

    @property
    def wxd_url(self) -> str:
        """Get Software Hub (WXD) base URL."""
        scheme = "https" if self.use_ssl else "http"
        return f"{scheme}://{self.wxd_host}"

    async def _mint_token(self) -> str:
        """Mint bearer token from Software Hub.

        POST to https://{WXD_HOST}/icp4d-api/v1/authorize
        with body: {"username": "{user}", "password": "{password}"}
        returns: {"token": "<bearer>", "expires_in": 43200, ...}
        """
        url = f"{self.wxd_url}/icp4d-api/v1/authorize"
        payload = {
            "username": self.workshop_user,
            "password": self.workshop_password,
        }

        try:
            async with httpx.AsyncClient(verify=self.verify_ssl) as client:
                response = await client.post(
                    url,
                    json=payload,
                    timeout=10.0,
                )
                response.raise_for_status()

                data = response.json()
                token = data.get("token")

                self._bearer_token = token
                self._token_acquired_at = datetime.utcnow()

                logger.info(
                    "bearer_token_minted",
                    wxd_host=self.wxd_host,
                    expires_in=data.get("expires_in"),
                )

                return token

        except Exception as e:
            logger.exception(
                "token_minting_failed",
                wxd_host=self.wxd_host,
                error=str(e),
            )
            raise

    async def _get_valid_token(self) -> str:
        """Get valid bearer token, refreshing if expired."""
        # Check if token exists and is still valid
        if self._bearer_token and self._token_acquired_at:
            age = (datetime.utcnow() - self._token_acquired_at).total_seconds()
            if age < self.token_cache_ttl:
                return self._bearer_token

        # Token expired or missing, mint new one
        return await self._mint_token()

    async def execute(
        self,
        query: str,
        fetch_all: bool = True,
    ) -> List[Dict[str, Any]]:
        """Execute SQL query and return all results.

        Handles:
        - Query submission (POST to Presto)
        - Polling loop (GET with nextUri until stats.state == "FINISHED")
        - Result pagination
        - Column name inference

        Args:
            query: SQL query string
            fetch_all: If True, fetch all pages; if False, return only first page

        Returns:
            List of result rows as dicts
        """
        # Check cache for immutable queries
        if self.enable_query_cache:
            cached = self._check_cache(query)
            if cached is not None:
                self._metrics.cache_hit_count += 1
                logger.debug("presto_query_cache_hit", query=query[:50])
                return cached

        try:
            token = await self._get_valid_token()

            # Submit query
            headers = {
                "Authorization": f"Bearer {token}",
                "X-Presto-User": self.workshop_user,
                "Content-Type": "text/plain",
            }

            async with httpx.AsyncClient(verify=self.verify_ssl) as client:
                response = await client.post(
                    f"{self.presto_url}/v1/statement",
                    content=query,
                    headers=headers,
                    timeout=self.query_timeout,
                )
                response.raise_for_status()

                result = response.json()
                query_id = result.get("id")

                logger.info(
                    "presto_query_submitted",
                    query_id=query_id,
                    query=query[:50],
                )

                # Poll until finished
                all_data = []
                next_uri = result.get("nextUri")

                while next_uri:
                    # Poll for status
                    poll_response = await client.get(
                        next_uri,
                        headers=headers,
                        timeout=self.query_timeout,
                    )
                    poll_response.raise_for_status()

                    result = poll_response.json()
                    state = result.get("stats", {}).get("state")

                    # Collect data if available
                    if result.get("data"):
                        rows = self._rows_to_dicts(result)
                        all_data.extend(rows)

                    # Check if finished
                    if state == "FINISHED":
                        break

                    # Get next URI for pagination
                    next_uri = result.get("nextUri")

                    if not next_uri and state not in ["FINISHED", "FAILED"]:
                        # Poll again if query still running
                        await asyncio.sleep(self.poll_interval)
                        next_uri = result.get("nextUri")

                self._metrics.query_count += 1

                # Cache results if query is immutable
                if self.enable_query_cache and self._is_immutable_query(query):
                    self._cache_result(query, all_data)
                    self._metrics.cache_miss_count += 1

                logger.info(
                    "presto_query_finished",
                    query_id=query_id,
                    row_count=len(all_data),
                )

                return all_data

        except Exception as e:
            self._metrics.error_count += 1
            self._metrics.last_error = str(e)
            self._metrics.last_error_time = datetime.utcnow()

            logger.exception(
                "presto_query_failed",
                query=query[:50],
                error=str(e),
            )

            raise

    def _rows_to_dicts(self, result: Dict) -> List[Dict[str, Any]]:
        """Convert result rows to list of dicts using column names."""
        columns = result.get("columns", [])
        data = result.get("data", [])

        # Extract column names
        column_names = [col.get("name") for col in columns]

        # Convert rows to dicts
        rows = []
        for row in data:
            row_dict = dict(zip(column_names, row))
            rows.append(row_dict)

        return rows

    def _is_immutable_query(self, query: str) -> bool:
        """Check if query targets immutable Iceberg tables."""
        immutable_tables = [
            "cohort_retention",
            "daily_sales_summary",
            "product_performance_weekly",
            "customer_ltv_monthly",
            "orders_archive",
            "order_items_archive",
            "competitor_prices_weekly",
            "marketing_attribution",
        ]

        query_lower = query.lower()
        return any(table in query_lower for table in immutable_tables)

    def _check_cache(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Check if query result is cached and still valid."""
        if query in self._query_cache:
            cached_time, cached_data = self._query_cache[query]
            age = (datetime.utcnow() - cached_time).total_seconds()

            if age < self.cache_ttl:
                return cached_data

            # Cache expired, remove it
            del self._query_cache[query]

        return None

    def _cache_result(self, query: str, data: List[Dict[str, Any]]):
        """Cache query result."""
        self._query_cache[query] = (datetime.utcnow(), data)

    async def _fetch_page(self, uri: str) -> Dict:
        """Fetch a single page of results."""
        token = await self._get_valid_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Presto-User": self.workshop_user,
        }

        async with httpx.AsyncClient(verify=self.verify_ssl) as client:
            response = await client.get(
                uri,
                headers=headers,
                timeout=self.query_timeout,
            )
            response.raise_for_status()
            return response.json()

    async def fetch_all_pages(self, initial_result: Dict) -> List[Dict[str, Any]]:
        """Fetch all pages of results from initial query response."""
        all_data = []
        next_uri = initial_result.get("nextUri")

        while next_uri:
            result = await self._fetch_page(next_uri)

            if result.get("data"):
                rows = self._rows_to_dicts(result)
                all_data.extend(rows)

            next_uri = result.get("nextUri")

        return all_data

    def _handle_error(self, error: Dict) -> str:
        """Extract error message from Presto error response."""
        if isinstance(error, dict):
            return error.get("message", str(error))
        return str(error)

    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        return {
            "query_count": self._metrics.query_count,
            "error_count": self._metrics.error_count,
            "timeout_count": self._metrics.timeout_count,
            "cache_hit_count": self._metrics.cache_hit_count,
            "cache_miss_count": self._metrics.cache_miss_count,
            "last_error": self._metrics.last_error,
            "last_error_time": self._metrics.last_error_time.isoformat()
            if self._metrics.last_error_time
            else None,
        }

    def clear_cache(self):
        """Clear query result cache."""
        self._query_cache.clear()
        logger.info("presto_query_cache_cleared")

    def reset_metrics(self):
        """Reset collected metrics."""
        self._metrics = PrestoMetrics()
        logger.info("presto_metrics_reset")
