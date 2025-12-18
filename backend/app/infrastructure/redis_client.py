"""
Redis client configuration
"""

import redis
from app.infrastructure.settings import get_settings

settings = get_settings()

# Create Redis connection pool
redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)
redis_client = redis.Redis(connection_pool=redis_pool)


def get_redis() -> redis.Redis:
    """Get Redis client instance"""
    return redis_client


def ping_redis() -> bool:
    """Ping Redis to check connectivity"""
    try:
        return redis_client.ping()
    except Exception:
        return False


