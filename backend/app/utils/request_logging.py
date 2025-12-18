"""
Request logging middleware for structured logs with metrics
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.infrastructure.logging_config import trace_id_context
from app.utils.metrics import record_http_request

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log HTTP requests with structured JSON logs.
    
    Logs include:
    - timestamp, level, message
    - trace_id (from TraceIDMiddleware)
    - path, method, status_code, duration_ms
    - actor_id, actor_role (if available from request state)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Get trace_id (set by TraceIDMiddleware)
        trace_id = trace_id_context.get()
        
        # Get actor info if available (set by auth middleware)
        # Try to get from principal if available (set by require_auth)
        try:
            from app.auth.oidc import Principal
            principal = getattr(request.state, "principal", None)
            if principal and isinstance(principal, Principal):
                if hasattr(principal, "user_id"):
                    actor_id = str(principal.user_id)
                else:
                    actor_id = None
                actor_role = ",".join(principal.roles) if principal.roles else None
            else:
                actor_id = getattr(request.state, "actor_id", None)
                actor_role = getattr(request.state, "actor_role", None)
        except Exception:
            # Fallback if principal not available
            actor_id = getattr(request.state, "actor_id", None)
            actor_role = getattr(request.state, "actor_role", None)
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            error = None
        except Exception as e:
            status_code = 500
            error = str(e)
            raise
        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log request
            log_data = {
                "trace_id": trace_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
            }
            
            if actor_id:
                log_data["actor_id"] = str(actor_id)
            if actor_role:
                log_data["actor_role"] = actor_role
            
            if error:
                log_data["error"] = error
                logger.error("Request failed", extra=log_data)
            elif status_code >= 500:
                logger.error("Request failed", extra=log_data)
            elif status_code >= 400:
                logger.warning("Request client error", extra=log_data)
            else:
                logger.info("Request completed", extra=log_data)
            
            # Record metrics
            record_http_request(
                path=request.url.path,
                method=request.method,
                status_code=status_code,
                duration_seconds=duration_ms / 1000,
            )
        
        return response

