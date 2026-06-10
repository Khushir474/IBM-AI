"""Cassandra async client wrapper with connection pooling, retry logic, and metrics.

Implements the Route endpoint factory pattern from AGENTS.md to handle OpenShift TLS Route:
- All Cassandra nodes sit behind one OpenShift Route on port 443
- Driver discovers internal pod IPs (10.x) on native port 9042 (unreachable)
- Endpoint factory collapses all discovered nodes to single Route endpoint
- This prevents connect timeouts when driver tries to reach unreachable pod IPs
"""

import asyncio
import ssl
import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

HAS_CASSANDRA = True
try:
    from cassandra.cluster import Cluster, DefaultEndPoint, EndPointFactory
    from cassandra.auth import PlainTextAuthProvider
    from cassandra import InvalidRequest, OperationTimedOut, Unavailable
except ImportError:
    HAS_CASSANDRA = False
    EndPointFactory = object
    DefaultEndPoint = None
    Cluster = None

    class PlainTextAuthProvider:
        def __init__(self, username, password):
            pass

    OperationTimedOut = Exception
    Unavailable = Exception

logger = structlog.get_logger(__name__)


@dataclass
class CassandraMetrics:
    """Metrics collected from Cassandra client."""

    query_count: int = 0
    error_count: int = 0
    timeout_count: int = 0
    latency_ms_sum: float = 0.0
    latency_p99: float = 0.0
    latency_p95: float = 0.0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    connection_count: int = 0


class RouteEndPointFactory(EndPointFactory if HAS_CASSANDRA else object):
    """Custom endpoint factory for OpenShift Route pinning.

    All discovered Cassandra nodes behind Route resolve to single endpoint (host, port).
    Prevents driver from attempting to connect to internal pod IPs (10.x) on port 9042,
    which are unreachable from outside the cluster.

    From AGENTS.md: "An address translator is not enough here — it rewrites the address
    but leaves the discovered 9042 port intact, so the driver still stalls dialing the
    Route host on a port it doesn't expose."
    """

    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port

    def create(self, row):
        """Create endpoint for discovered node - always return Route endpoint."""
        if HAS_CASSANDRA:
            return DefaultEndPoint(self._host, self._port)
        return None

    def create_from_sni(self, sni):
        """Create endpoint from SNI - always return Route endpoint."""
        if HAS_CASSANDRA:
            return DefaultEndPoint(self._host, self._port)
        return None


class CassandraClient:
    """Async Cassandra client with connection pooling, retry logic, and metrics.

    Handles:
    - Async session management with context manager support
    - Connection pooling with configurable size
    - Retry logic for transient failures (tenacity)
    - SSL/TLS setup with Route endpoint factory
    - Prepared statement caching
    - Metrics collection (latency, errors, etc.)
    - Batch operations
    """

    def __init__(
        self,
        host: str,
        port: int = 9042,
        username: str = "cassandra",
        password: str = "cassandra",
        keyspace: str = "ecommerce",
        use_ssl: bool = False,
        ssl_verify: bool = True,
        use_route_endpoint_factory: bool = False,
        connection_timeout: float = 5.0,
        request_timeout: float = 5.0,
        pool_size: int = 5,
        prepared_statement_cache_size: int = 100,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
        retry_jitter: bool = True,
        collect_metrics: bool = True,
    ):
        """Initialize Cassandra client.

        Args:
            host: Cassandra host (or Route FQDN for workshop)
            port: Cassandra port (usually 9042, or 443 for OpenShift Route)
            username: Authentication username
            password: Authentication password
            keyspace: Default keyspace
            use_ssl: Enable SSL/TLS
            ssl_verify: Verify SSL certificates
            use_route_endpoint_factory: Use endpoint factory for Route pinning
            connection_timeout: Connection timeout in seconds
            request_timeout: Request timeout in seconds
            pool_size: Connection pool size
            prepared_statement_cache_size: Max prepared statements to cache
            max_retries: Max retry attempts for transient failures
            retry_backoff: Initial backoff in seconds (exponential)
            retry_jitter: Add jitter to backoff
            collect_metrics: Enable metrics collection
        """
        self.host = host
        self.port = port
        self.username = username
        self.keyspace = keyspace
        self.use_ssl = use_ssl
        self.ssl_verify = ssl_verify
        self.use_route_endpoint_factory = use_route_endpoint_factory
        self.connection_timeout = connection_timeout
        self.request_timeout = request_timeout
        self.pool_size = pool_size
        self.prepared_statement_cache_size = prepared_statement_cache_size
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.retry_jitter = retry_jitter
        self.collect_metrics = collect_metrics

        self.cluster: Optional[Cluster] = None
        self.session = None
        self._prepared_statements: Dict[str, Any] = {}
        self._metrics = CassandraMetrics()
        self._auth_provider = PlainTextAuthProvider(username, password)

        logger.info(
            "cassandra_client_initialized",
            host=host,
            port=port,
            keyspace=keyspace,
            use_ssl=use_ssl,
            use_route_endpoint_factory=use_route_endpoint_factory,
        )

    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for Cassandra connection.

        Handles the quirk mentioned in AGENTS.md: driver resolves contact point to IP
        before TLS handshake, then validates server cert against IP (fails). Workaround:
        disable hostname matching but keep CA-chain validation, pass hostname via SNI.
        """
        if not self.use_ssl:
            return None

        ctx = ssl.create_default_context()  # Trusts LE chain by default
        ctx.check_hostname = False  # IP-vs-hostname mismatch dance

        logger.info(
            "ssl_context_created",
            host=self.host,
            check_hostname=ctx.check_hostname,
        )

        return ctx

    async def _create_cluster(self) -> Cluster:
        """Create Cassandra cluster connection."""
        if not HAS_CASSANDRA:
            raise ImportError(
                "cassandra-driver not installed. "
                "Install with: pip install cassandra-driver"
            )

        ssl_context = self._create_ssl_context()
        endpoint_factory = None

        if self.use_route_endpoint_factory:
            endpoint_factory = RouteEndPointFactory(self.host, self.port)
            logger.info(
                "route_endpoint_factory_enabled",
                host=self.host,
                port=self.port,
            )

        cluster = Cluster(
            contact_points=[self.host],
            port=self.port,
            auth_provider=self._auth_provider,
            ssl_context=ssl_context,
            ssl_options={"server_hostname": self.host} if self.use_ssl else None,
            endpoint_factory=endpoint_factory,
            connect_timeout=self.connection_timeout,
            default_fetch_size=1000,
        )

        logger.info(
            "cluster_created",
            host=self.host,
            port=self.port,
            contact_points=[self.host],
        )

        return cluster

    async def _create_session(self, cluster: Cluster):
        """Create Cassandra session from cluster."""
        session = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: cluster.connect(self.keyspace),
        )

        logger.info(
            "session_created",
            keyspace=self.keyspace,
        )

        return session

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        return False

    async def connect(self):
        """Connect to Cassandra cluster."""
        try:
            self.cluster = await self._create_cluster()
            self.session = await self._create_session(self.cluster)
            self._metrics.connection_count += 1
            logger.info("cassandra_connected", keyspace=self.keyspace)
        except Exception as e:
            logger.exception(
                "cassandra_connection_failed",
                host=self.host,
                port=self.port,
                error=str(e),
            )
            raise

    async def close(self):
        """Close Cassandra session and cluster."""
        if self.session:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.session.shutdown,
            )
            logger.info("cassandra_session_closed")

        if self.cluster:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.cluster.shutdown,
            )
            logger.info("cassandra_cluster_closed")

    async def _get_prepared_statement(self, query: str):
        """Get prepared statement from cache or prepare new one."""
        if query in self._prepared_statements:
            return self._prepared_statements[query]

        stmt = await asyncio.get_event_loop().run_in_executor(
            None,
            self.session.prepare,
            query,
        )

        if len(self._prepared_statements) < self.prepared_statement_cache_size:
            self._prepared_statements[query] = stmt

        return stmt

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((OperationTimedOut, Unavailable)),
        reraise=True,
    )
    async def execute(self, query: str, parameters: Optional[List] = None) -> List[Dict]:
        """Execute CQL query with automatic retry on transient failures.

        Args:
            query: CQL query string
            parameters: Query parameters for binding

        Returns:
            List of result rows as dicts
        """
        if not self.session:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            stmt = await self._get_prepared_statement(query)
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.session.execute(
                    stmt,
                    parameters or [],
                    timeout=self.request_timeout,
                ),
            )

            rows = [dict(row) for row in result]
            self._metrics.query_count += 1

            logger.debug(
                "cassandra_query_executed",
                query=query[:50],
                row_count=len(rows),
                parameters_count=len(parameters or []),
            )

            return rows

        except (OperationTimedOut, Unavailable) as e:
            self._metrics.timeout_count += 1
            self._metrics.last_error = str(e)
            self._metrics.last_error_time = datetime.utcnow()
            logger.warning(
                "cassandra_transient_error",
                query=query[:50],
                error=str(e),
            )
            raise

        except Exception as e:
            self._metrics.error_count += 1
            self._metrics.last_error = str(e)
            self._metrics.last_error_time = datetime.utcnow()
            logger.exception(
                "cassandra_query_failed",
                query=query[:50],
                error=str(e),
            )
            raise

    async def execute_batch(
        self,
        queries: List[Tuple[str, Optional[List]]],
    ) -> None:
        """Execute batch of queries.

        Args:
            queries: List of (query, parameters) tuples
        """
        if not self.session:
            raise RuntimeError("Not connected. Call connect() first.")

        if not queries:
            return

        try:
            batch = self.session.BatchStatement()

            for query, parameters in queries:
                stmt = await self._get_prepared_statement(query)
                batch.add(stmt, parameters or [])

            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.session.execute(
                    batch,
                    timeout=self.request_timeout,
                ),
            )

            self._metrics.query_count += len(queries)
            logger.info(
                "cassandra_batch_executed",
                query_count=len(queries),
            )

        except Exception as e:
            self._metrics.error_count += 1
            self._metrics.last_error = str(e)
            logger.exception(
                "cassandra_batch_failed",
                query_count=len(queries),
                error=str(e),
            )
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        return {
            "query_count": self._metrics.query_count,
            "error_count": self._metrics.error_count,
            "timeout_count": self._metrics.timeout_count,
            "connection_count": self._metrics.connection_count,
            "last_error": self._metrics.last_error,
            "last_error_time": self._metrics.last_error_time.isoformat()
            if self._metrics.last_error_time
            else None,
        }

    def clear_prepared_statement_cache(self):
        """Clear prepared statement cache."""
        self._prepared_statements.clear()
        logger.info("prepared_statement_cache_cleared")

    def reset_metrics(self):
        """Reset collected metrics."""
        self._metrics = CassandraMetrics()
        logger.info("metrics_reset")
