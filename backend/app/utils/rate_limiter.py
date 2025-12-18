"""
Rate limiting middleware using Redis-backed sliding window
"""

import time
import logging
from typing import Optional, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.infrastructure.redis_client import get_redis
from app.infrastructure.settings import get_settings
from app.infrastructure.logging_config import trace_id_context

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""
    pass


class RateLimiter:
    """
    Redis-backed rate limiter using sliding window algorithm.
    
    Uses Redis sorted sets to implement a sliding window rate limiter.
    Key format: "ratelimit:{endpoint_group}:{identifier}"
    """
    
    def __init__(
        self,
        redis_client,
        limit: int,
        window_seconds: int = 60,
    ):
        """
        Initialize rate limiter.
        
        Args:
            redis_client: Redis client instance
            limit: Maximum number of requests allowed
            window_seconds: Time window in seconds (default: 60 for per-minute limits)
        """
        self.redis = redis_client
        self.limit = limit
        self.window_seconds = window_seconds
    
    def get_key(self, endpoint_group: str, identifier: str) -> str:
        """Generate Redis key for rate limit"""
        return f"ratelimit:{endpoint_group}:{identifier}"
    
    def check_rate_limit(
        self,
        endpoint_group: str,
        identifier: str,
    ) -> Tuple[bool, int, int, int]:
        """
        Check if request is within rate limit.
        
        Args:
            endpoint_group: Endpoint group (webhook, admin, api)
            identifier: Identifier (typically IP address)
        
        Returns:
            Tuple of (is_allowed, remaining, limit, reset_time)
            - is_allowed: True if request is allowed
            - remaining: Number of requests remaining
            - limit: Total limit
            - reset_time: Unix timestamp when limit resets
        """
        key = self.get_key(endpoint_group, identifier)
        now = int(time.time())
        window_start = now - self.window_seconds
        
        # Clean old entries (outside window)
        self.redis.zremrangebyscore(key, 0, window_start)
        
        # Count requests in current window
        current_count = self.redis.zcard(key)
        
        # Check if limit exceeded
        if current_count >= self.limit:
            # Calculate reset time (oldest entry + window_seconds)
            oldest_entry = self.redis.zrange(key, 0, 0, withscores=True)
            if oldest_entry:
                reset_time = int(oldest_entry[0][1]) + self.window_seconds
            else:
                reset_time = now + self.window_seconds
            
            return False, 0, self.limit, reset_time
        
        # Add current request to window
        self.redis.zadd(key, {str(now): now})
        self.redis.expire(key, self.window_seconds + 10)  # Expire slightly after window
        
        # Recalculate remaining (after adding)
        current_count = self.redis.zcard(key)
        remaining = max(0, self.limit - current_count)
        
        # Reset time is now + window_seconds
        reset_time = now + self.window_seconds
        
        return True, remaining, self.limit, reset_time


def get_client_identifier(request: Request) -> str:
    """
    Extract client identifier from request (IP address).
    
    Handles proxy headers (X-Forwarded-For, X-Real-IP) for production deployments.
    """
    # Check X-Forwarded-For header (for proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one
        client_ip = forwarded_for.split(",")[0].strip()
        return client_ip
    
    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fall back to direct client IP
    if request.client:
        return request.client.host
    
    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    
    Configures rate limits per endpoint group:
    - /webhooks/v1/* -> webhook
    - /admin/v1/* -> admin
    - /api/v1/* -> api
    """
    
    def __init__(self, app, redis_client):
        super().__init__(app)
        self.redis = redis_client
        self.settings = get_settings()
        
        # Initialize rate limiters per endpoint group
        self.limiters = {
            "webhook": RateLimiter(
                redis_client=redis_client,
                limit=self.settings.RL_WEBHOOK_PER_MIN,
                window_seconds=60,
            ),
            "admin": RateLimiter(
                redis_client=redis_client,
                limit=self.settings.RL_ADMIN_PER_MIN,
                window_seconds=60,
            ),
            "api": RateLimiter(
                redis_client=redis_client,
                limit=self.settings.RL_API_PER_MIN,
                window_seconds=60,
            ),
        }
    
    def get_endpoint_group(self, path: str) -> Optional[str]:
        """Determine endpoint group from path"""
        if path.startswith("/webhooks/v1/"):
            return "webhook"
        elif path.startswith("/admin/v1/"):
            return "admin"
        elif path.startswith("/api/v1/"):
            return "api"
        return None
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/ready", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        endpoint_group = self.get_endpoint_group(request.url.path)
        if not endpoint_group:
            # No rate limiting for non-API endpoints
            return await call_next(request)
        
        identifier = get_client_identifier(request)
        limiter = self.limiters[endpoint_group]
        
        # Check rate limit
        is_allowed, remaining, limit, reset_time = limiter.check_rate_limit(
            endpoint_group=endpoint_group,
            identifier=identifier,
        )
        
        # Get trace_id for logging
        trace_id = trace_id_context.get("unknown")
        
        if not is_allowed:
            # Record metrics
            from app.utils.metrics import record_rate_limit_exceeded
            record_rate_limit_exceeded(group=endpoint_group)
            
            # Rate limit exceeded - log security event
            from app.utils.security_logging import log_security_event, track_abuse_pattern, log_repeated_abuse
            
            log_security_event(
                action="RATE_LIMIT_EXCEEDED",
                details={
                    "endpoint_group": endpoint_group,
                    "identifier": identifier,
                    "path": request.url.path,
                    "method": request.method,
                },
                trace_id=trace_id,
            )
            
            # Check for repeated abuse (especially on admin endpoints)
            if endpoint_group == "admin":
                abuse_detected = track_abuse_pattern(
                    redis_client=self.redis,
                    endpoint_group=endpoint_group,
                    identifier=identifier,
                    threshold=5,  # 5 violations in 10 minutes
                    window_seconds=600,  # 10 minutes
                )
                
                if abuse_detected:
                    # Log repeated abuse (would normally write AuditLog but we don't have DB here)
                    # The abuse detection itself is logged above
                    violation_count = self.redis.zcard(f"abuse:{endpoint_group}:{identifier}")
                    logger.error(
                        f"Repeated abuse on admin endpoint: identifier={identifier}, "
                        f"violations={violation_count}, trace_id={trace_id}"
                    )
            
            # Return 429 with standard error format
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": f"Rate limit exceeded. Maximum {limit} requests per minute.",
                        "details": {
                            "endpoint_group": endpoint_group,
                            "reset_at": reset_time,
                        },
                        "trace_id": trace_id,
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                },
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response

