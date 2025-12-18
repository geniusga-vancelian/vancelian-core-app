"""
Global exception handlers
"""

from typing import Any, Dict
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.utils.trace_id import get_trace_id


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions"""
    trace_id = get_trace_id(request)

    error_response: Dict[str, Any] = {
        "error": {
            "code": f"HTTP_{exc.status_code}",
            "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            "trace_id": trace_id,
        }
    }

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation exceptions"""
    trace_id = get_trace_id(request)

    error_response: Dict[str, Any] = {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": exc.errors(),
            "trace_id": trace_id,
        }
    }

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response,
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions"""
    trace_id = get_trace_id(request)

    error_response: Dict[str, Any] = {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An internal error occurred",
            "trace_id": trace_id,
        }
    }

    # Log the actual exception (in production, don't expose details)
    import logging
    logger = logging.getLogger(__name__)
    logger.exception("Unhandled exception", exc_info=exc, extra={"trace_id": trace_id})

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response,
    )

