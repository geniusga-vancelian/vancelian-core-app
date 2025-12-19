"""
FastAPI application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.infrastructure.settings import get_settings
from app.infrastructure.logging_config import setup_logging
from app.api.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)
from app.api.public.health import router as health_router
from app.api.public.metrics import router as metrics_router
from app.api.v1 import router as api_v1_router
from app.api.admin import router as admin_router
from app.api.webhooks import router as webhooks_router
from app.utils.trace_id import TraceIDMiddleware
from app.utils.request_logging import RequestLoggingMiddleware
from app.utils.security_headers import SecurityHeadersMiddleware
from app.utils.rate_limiter import RateLimitMiddleware
from app.infrastructure.redis_client import get_redis

# Setup logging
setup_logging()

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Vancelian Core API",
    description="Core API for Vancelian platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware IMMEDIATELY after app creation (before other middlewares and routers)
# This ensures CORS headers are applied to all routes including webhooks
# Configuration comes from settings (can be overridden via environment variables in docker-compose)
if settings.CORS_ENABLED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins_list,
        allow_methods=settings.cors_allow_methods_list if settings.cors_allow_methods_list else ["*"],
        allow_headers=settings.cors_allow_headers_list if settings.cors_allow_headers_list else ["*"],
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    )

# Add custom middlewares (order matters - first added is outermost)
app.add_middleware(TraceIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
# Initialize Redis client for rate limiting
redis_client = get_redis()
app.add_middleware(RateLimitMiddleware, redis_client=redis_client)

# Register exception handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Register routers
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(api_v1_router)
app.include_router(admin_router)
app.include_router(webhooks_router)

# Conditionally include dev router if DEV_MODE is enabled
if settings.DEV_MODE:
    try:
        from app.api.dev import router as dev_router
        app.include_router(dev_router)
    except ImportError:
        pass  # Dev router not available

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Vancelian Core API",
        "version": "1.0.0",
        "status": "running",
    }
