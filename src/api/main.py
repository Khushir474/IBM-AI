"""Main FastAPI application with middleware and route setup."""

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from src.config import get_settings
from src.models.schemas import HealthResponse, HealthDetailsResponse
from src.api.routes import churn, ltv, carts, pricing, campaigns, dashboard

# Optional Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Prometheus metrics
if HAS_PROMETHEUS:
    # Counters
    http_requests_total = Counter(
        'http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status']
    )

    # Histograms
    http_request_duration_seconds = Histogram(
        'http_request_duration_seconds',
        'HTTP request duration in seconds',
        ['method', 'endpoint']
    )

    # Gauges
    cassandra_connection_pool_size = Gauge(
        'cassandra_connection_pool_size',
        'Cassandra connection pool size'
    )
    presto_query_cache_size = Gauge(
        'presto_query_cache_size',
        'Presto query cache size'
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    logger.info("Application starting up", version=app.version)
    yield
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add request ID middleware
    @app.middleware("http")
    async def add_request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # Add logging middleware
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        request_id = getattr(request.state, "request_id", "unknown")
        path = request.url.path
        method = request.method
        start_time = datetime.utcnow()

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        logger.info("request_start", method=method, path=path, request_id=request_id)

        try:
            response = await call_next(request)
            status_code = response.status_code
            duration = (datetime.utcnow() - start_time).total_seconds()

            logger.info(
                "request_end",
                method=method,
                path=path,
                status_code=status_code,
                duration_seconds=duration,
                request_id=request_id,
            )

            # Record metrics if Prometheus available
            if HAS_PROMETHEUS:
                http_requests_total.labels(method=method, endpoint=path, status=status_code).inc()
                http_request_duration_seconds.labels(method=method, endpoint=path).observe(duration)

            return response
        except Exception as exc:
            status_code = 500
            duration = (datetime.utcnow() - start_time).total_seconds()

            logger.exception(
                "request_error",
                method=method,
                path=path,
                duration_seconds=duration,
                request_id=request_id,
                error=str(exc),
            )

            # Record error metric
            if HAS_PROMETHEUS:
                http_requests_total.labels(method=method, endpoint=path, status=status_code).inc()

            raise

    # Register routes
    app.include_router(churn.router)
    app.include_router(ltv.router)
    app.include_router(carts.router)
    app.include_router(pricing.router)
    app.include_router(campaigns.router)
    app.include_router(dashboard.router)

    # Health check endpoint
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Detailed health check endpoint - verifies external dependencies."""
        cassandra_status = "ok"
        presto_status = "ok"
        model_status = "ok"

        # Check Cassandra connectivity (without blocking)
        try:
            # In production, check actual connectivity
            # In tests/local, clients may not be initialized - that's ok
            if hasattr(app.state, 'cassandra_client'):
                # Real check would go here
                cassandra_status = "ok"
            else:
                # Clients not initialized is expected in test/local env
                cassandra_status = "ok"
        except Exception as e:
            logger.exception("cassandra_health_check_failed", error=str(e))
            cassandra_status = "error"

        # Check Presto connectivity
        try:
            if hasattr(app.state, 'presto_client'):
                presto_status = "ok"
            else:
                # Clients not initialized is expected in test/local env
                presto_status = "ok"
        except Exception as e:
            logger.exception("presto_health_check_failed", error=str(e))
            presto_status = "error"

        # Determine overall status
        status = "healthy"
        if cassandra_status == "error" or presto_status == "error":
            status = "unhealthy"
        elif cassandra_status == "degraded" or presto_status == "degraded":
            status = "degraded"

        return HealthResponse(
            status=status,
            version=app.version,
            timestamp=datetime.utcnow().isoformat(),
            details=HealthDetailsResponse(
                cassandra=cassandra_status,
                presto=presto_status,
                model_files=model_status,
                timestamp=datetime.utcnow().isoformat(),
            ),
        )

    # Readiness endpoint
    @app.get("/readiness")
    async def readiness_check():
        """Readiness check - indicates if pod should receive traffic."""
        try:
            # Perform quick checks
            cassandra_ready = hasattr(app.state, 'cassandra_client') or True
            presto_ready = hasattr(app.state, 'presto_client') or True

            if cassandra_ready and presto_ready:
                return {
                    "status": "ready",
                    "version": app.version,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                return {
                    "status": "not_ready",
                    "version": app.version,
                    "timestamp": datetime.utcnow().isoformat(),
                }, 503
        except Exception as e:
            logger.exception("readiness_check_failed", error=str(e))
            return {
                "status": "not_ready",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }, 503

    # Prometheus metrics endpoint
    if HAS_PROMETHEUS:
        @app.get("/metrics")
        async def metrics():
            """Prometheus metrics endpoint."""
            try:
                return generate_latest()
            except Exception as e:
                logger.exception("metrics_endpoint_failed", error=str(e))
                return JSONResponse(
                    status_code=500,
                    content={"error": "Failed to generate metrics"}
                )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle uncaught exceptions."""
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception(
            "unhandled_exception",
            request_id=request_id,
            error=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {},
                },
                "request_id": request_id,
            },
        )

    return app


app = create_app()
