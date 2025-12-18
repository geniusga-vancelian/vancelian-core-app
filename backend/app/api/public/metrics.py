"""
Prometheus metrics endpoint
"""

import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, status, Header, Depends
from fastapi.responses import Response

from app.infrastructure.settings import get_settings
from app.utils.metrics import get_metrics_output, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)

router = APIRouter()


async def verify_metrics_access(
    request: Request,
    x_metrics_token: Optional[str] = Header(None, alias="X-Metrics-Token"),
) -> bool:
    """
    Verify access to metrics endpoint.
    
    Access is granted if:
    - METRICS_PUBLIC=true, OR
    - METRICS_TOKEN is set and matches X-Metrics-Token header, OR
    - User is authenticated with ADMIN/COMPLIANCE/OPS role (Bearer token)
    
    Returns True if access is granted, raises HTTPException otherwise.
    """
    settings = get_settings()
    
    # Public access
    if settings.METRICS_PUBLIC:
        return True
    
    # Token-based access
    if settings.METRICS_TOKEN and x_metrics_token:
        if x_metrics_token == settings.METRICS_TOKEN:
            return True
    
    # Admin role access (via OIDC Bearer token)
    # Try to verify JWT token if Authorization header is present
    authorization = request.headers.get("Authorization", "")
    if authorization and authorization.startswith("Bearer "):
        try:
            from app.auth.oidc import verify_jwt_token
            from app.core.security.models import Role
            token = authorization.split(" ", 1)[1]
            principal = verify_jwt_token(token)
            # Check if user has ADMIN, COMPLIANCE, or OPS role
            if principal.roles and any(
                r.upper() in ["ADMIN", "COMPLIANCE", "OPS"] for r in principal.roles
            ):
                return True
        except Exception:
            # Token verification failed - fall through to deny access
            pass
    
    # Access denied
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access to metrics endpoint denied. Set METRICS_PUBLIC=true or provide valid METRICS_TOKEN or ADMIN/COMPLIANCE/OPS role.",
    )


@router.get(
    "/metrics",
    summary="Prometheus metrics endpoint",
    description="Expose Prometheus metrics for observability. Protected by default (METRICS_PUBLIC=false).",
)
async def get_metrics(
    request: Request,
    _: bool = Depends(verify_metrics_access),
) -> Response:
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus exposition format.
    
    Protection:
    - If METRICS_PUBLIC=false: Requires METRICS_TOKEN header or ADMIN/COMPLIANCE/OPS role
    - If METRICS_PUBLIC=true: Public access
    """
    try:
        metrics_output = get_metrics_output()
        return Response(
            content=metrics_output,
            media_type=CONTENT_TYPE_LATEST,
        )
    except Exception as e:
        logger.error(f"Error generating metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating metrics",
        )
