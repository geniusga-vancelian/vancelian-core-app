"""
Health check endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.infrastructure.database import get_db
from app.infrastructure.redis_client import ping_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Basic health check"""
    return {"status": "ok"}


@router.get("/ready")
async def ready(db: Session = Depends(get_db)):
    """
    Readiness check - verifies DB and Redis connectivity
    
    Returns:
    - 200 if all services are ready
    - 503 if any service is not ready
    """
    from fastapi.responses import JSONResponse
    
    checks = {
        "status": "ok",
        "database": "unknown",
        "redis": "unknown",
    }

    # Check database
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
        checks["status"] = "not_ready"

    # Check Redis
    if ping_redis():
        checks["redis"] = "connected"
    else:
        checks["redis"] = "disconnected"
        checks["status"] = "not_ready"

    status_code = 200 if checks["status"] == "ok" else 503
    return JSONResponse(status_code=status_code, content=checks)

