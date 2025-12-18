"""
Security headers middleware
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.infrastructure.settings import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    
    Sets:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - Referrer-Policy: no-referrer
    - Permissions-Policy: camera=(), microphone=(), geolocation=()
    - Strict-Transport-Security: (only if ENABLE_HSTS env is set)
    """
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response"""
        response = await call_next(request)
        
        settings = get_settings()
        
        # Content Type Options - prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Frame Options - prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Referrer Policy - no referrer info leaked
        response.headers["Referrer-Policy"] = "no-referrer"
        
        # Permissions Policy - restrict browser features
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        
        # HSTS - only if explicitly enabled (not in local dev by default)
        if settings.ENABLE_HSTS:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

