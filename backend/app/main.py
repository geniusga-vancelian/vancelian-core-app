"""
FastAPI application entry point
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
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
# This ensures CORS headers are applied to all routes including webhooks and admin endpoints
# Configuration comes from settings (can be overridden via environment variables in docker-compose)
# DEV CORS origins for frontend-client (3000) and frontend-admin (3001)
DEV_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

if settings.CORS_ENABLED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_CORS_ORIGINS,  # Use explicit DEV origins for clarity
        allow_methods=["*"],  # Allow all methods for dev flexibility
        allow_headers=["*"],  # Allow all headers for dev flexibility (includes Authorization, Content-Type, etc.)
        allow_credentials=True,  # Required for frontend-admin uploads with Authorization headers
    )

# Add custom middlewares (order matters - first added is outermost)
app.add_middleware(TraceIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
# Initialize Redis client for rate limiting
redis_client = get_redis()
app.add_middleware(RateLimitMiddleware, redis_client=redis_client)

# Register exception handlers
from app.services.storage.exceptions import StorageNotConfiguredError

async def storage_not_configured_handler(request: Request, exc: StorageNotConfiguredError) -> JSONResponse:
    """Handle StorageNotConfiguredError - return 412 Precondition Failed"""
    from app.utils.trace_id import get_trace_id
    trace_id = get_trace_id(request)
    
    error_response = {
        "error": {
            "code": exc.code,
            "message": exc.message,
            "trace_id": trace_id,
        }
    }
    
    return JSONResponse(
        status_code=412,  # Precondition Failed
        content=error_response,
    )

app.add_exception_handler(StorageNotConfiguredError, storage_not_configured_handler)
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
