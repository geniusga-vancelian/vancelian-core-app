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

    # If detail is already a dict with "error" key, use it directly (preserving custom codes)
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        error_response: Dict[str, Any] = exc.detail.copy()
        # Ensure trace_id is present (use from detail if exists, otherwise use generated one)
        if "error" in error_response and isinstance(error_response["error"], dict):
            if "trace_id" not in error_response["error"]:
                error_response["error"]["trace_id"] = trace_id
    else:
        # Default format
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

    # Convert non-JSON-serializable objects in error details to strings
    def convert_non_serializable(obj):
        """Recursively convert non-JSON-serializable objects to strings"""
        from decimal import Decimal
        if isinstance(obj, (Decimal, Exception)):
            return str(obj)
        elif isinstance(obj, dict):
            return {key: convert_non_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [convert_non_serializable(item) for item in obj]
        elif isinstance(obj, (type, type(ValueError))):
            return str(obj)  # Convert exception classes to strings
        return obj

    error_details = convert_non_serializable(exc.errors())

    error_response: Dict[str, Any] = {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": error_details,
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



