"""
Admin API - Debug endpoints (DEV only)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.infrastructure.settings import get_settings
from app.auth.dependencies import require_admin_role
from app.auth.oidc import Principal

router = APIRouter()


@router.get(
    "/debug/cors",
    summary="Get CORS configuration (DEV only)",
    description="Returns current CORS configuration. Only available when DEV_MODE=True or ENV=local.",
)
async def get_cors_config(
    principal: Principal = Depends(require_admin_role()),
) -> dict:
    """Get CORS configuration (DEV only)"""
    settings = get_settings()
    
    # Only allow in dev mode or development/local environment
    env_lower = settings.ENV.lower()
    if not (settings.DEV_MODE or env_lower in ["local", "development", "dev"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NOT_FOUND"
        )
    
    return {
        "cors_enabled": settings.CORS_ENABLED,
        "allow_origins": settings.cors_allow_origins_list,
        "allow_credentials": settings.CORS_ALLOW_CREDENTIALS,
        "allow_methods": settings.cors_allow_methods_list,
        "allow_headers": settings.cors_allow_headers_list,
        "env_snapshot": {
            "ENV": settings.ENV,
            "DEV_MODE": settings.DEV_MODE,
            "CORS_ENABLED": settings.CORS_ENABLED,
        }
    }

