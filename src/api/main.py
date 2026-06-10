"""Main FastAPI application with middleware and route setup."""

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

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        logger.info("request_start", method=method, path=path, request_id=request_id)

        try:
            response = await call_next(request)
            status_code = response.status_code
            logger.info(
                "request_end",
                method=method,
                path=path,
                status_code=status_code,
                request_id=request_id,
            )
            return response
        except Exception as exc:
            logger.exception(
                "request_error",
                method=method,
                path=path,
                request_id=request_id,
                error=str(exc),
            )
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
        """Health check endpoint."""
        return HealthResponse(
            status="healthy",
            version=app.version,
            timestamp=datetime.utcnow().isoformat(),
            details=HealthDetailsResponse(
                cassandra="ok",
                presto="ok",
                model_files="ok",
                timestamp=datetime.utcnow().isoformat(),
            ),
        )

    # Readiness endpoint
    @app.get("/readiness")
    async def readiness_check():
        """Readiness check endpoint."""
        return {
            "status": "ready",
            "version": app.version,
            "timestamp": datetime.utcnow().isoformat(),
        }

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
