"""
Trace ID utilities for request tracking
"""

import uuid
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.infrastructure.logging_config import trace_id_context


def generate_trace_id() -> str:
    """Generate a new trace ID"""
    return str(uuid.uuid4())


class TraceIDMiddleware(BaseHTTPMiddleware):
    """Middleware to inject trace_id into request, logs, and response headers"""

    async def dispatch(self, request: Request, call_next):
        # Get trace_id from header (support multiple header names) or generate new one
        trace_id = (
            request.headers.get("X-Trace-ID") or
            request.headers.get("X-Request-Id") or
            request.headers.get("X-Correlation-Id") or
            generate_trace_id()
        )

        # Add trace_id to request state
        request.state.trace_id = trace_id

        # Set trace_id in context variable for logging
        trace_id_context.set(trace_id)

        # Process request
        response = await call_next(request)

        # Add trace_id to response header
        response.headers["X-Trace-ID"] = trace_id

        # Clear context variable after request
        trace_id_context.set(None)

        return response


def get_trace_id(request: Request) -> Optional[str]:
    """Get trace_id from request state"""
    return getattr(request.state, "trace_id", None)

