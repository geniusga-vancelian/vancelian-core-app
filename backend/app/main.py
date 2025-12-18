"""
Vancelian Core Backend - FastAPI application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

import logging

from app.infrastructure.settings import get_settings
from app.infrastructure.logging_config import setup_logging
from app.infrastructure.redis_client import get_redis

logger = logging.getLogger(__name__)
from app.utils.trace_id import TraceIDMiddleware
from app.utils.rate_limiter import RateLimitMiddleware
from app.utils.security_headers import SecurityHeadersMiddleware
from app.api.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)
from app.api.public.health import router as health_router
from app.api.public.metrics import router as metrics_router
from app.api.v1 import router as api_v1_router
from app.api.admin import router as admin_v1_router
from app.api.webhooks import router as webhooks_v1_router
from app.utils.request_logging import RequestLoggingMiddleware

settings = get_settings()

# DEV-ONLY routers (only loaded when DEV_MODE is enabled)
if settings.DEV_MODE:
    from app.api.dev import router as dev_router
else:
    dev_router = None

# Setup logging (logger is already defined above)
setup_logging(settings.LOG_LEVEL)

# Create FastAPI app
app = FastAPI(
    title="Vancelian Core API",
    description="Core backend API for Vancelian platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add middleware (order matters - executed in REVERSE order of addition)
# 1. Security headers (innermost - last to execute)
app.add_middleware(SecurityHeadersMiddleware)

# 2. Request logging (for metrics and structured logs)
app.add_middleware(RequestLoggingMiddleware)

# 3. Rate limiting
# Initialize Redis client (connection pool is lazy, won't crash on startup if Redis unavailable)
try:
    redis_client = get_redis()
    app.add_middleware(RateLimitMiddleware, redis_client=redis_client)
except Exception as e:
    # Log warning but don't crash - rate limiting will fail gracefully
    logger.warning(f"Redis client initialization failed (rate limiting disabled): {e}")

# 4. Trace ID (outermost - first to execute)
app.add_middleware(TraceIDMiddleware)

# 5. CORS middleware MUST be added LAST (so it executes FIRST)
# In FastAPI/Starlette, middlewares execute in REVERSE order of addition.
# By adding CORS last, it executes first and can handle OPTIONS preflight
# before any auth or other middleware runs.
if settings.CORS_ENABLED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins_list,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.cors_allow_methods_list,
        allow_headers=settings.cors_allow_headers_list,
        expose_headers=["X-Trace-ID"],  # Expose trace ID in responses
        max_age=600,  # Cache preflight for 10 minutes
    )
    logger.info(f"CORS enabled with origins: {settings.cors_allow_origins_list}")
    logger.info(f"CORS allowed methods: {settings.cors_allow_methods_list}")
    logger.info(f"CORS allowed headers: {settings.cors_allow_headers_list}")
else:
    logger.info("CORS disabled (CORS_ENABLED=false)")

# Global exception handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Register routers
app.include_router(health_router)
app.include_router(metrics_router)  # Metrics endpoint (protected)
app.include_router(api_v1_router)
app.include_router(admin_v1_router)
app.include_router(webhooks_v1_router)

# DEV-ONLY routers (only registered when DEV_MODE is enabled)
if settings.DEV_MODE and dev_router is not None:
    app.include_router(dev_router)
    logger.info("DEV-ONLY endpoints enabled at /dev/v1/* (DEV_MODE=true)")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Vancelian Core API",
        "version": "1.0.0",
        "status": "running",
    }

