"""
Admin API - System information endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.dependencies import require_admin_role
from app.auth.oidc import Principal
from app.infrastructure.settings import get_settings
from pydantic import BaseModel
from typing import Optional

router = APIRouter()
settings = get_settings()


class StorageInfoResponse(BaseModel):
    """Storage configuration information (safe for admin viewing)"""
    enabled: bool
    bucket: Optional[str] = None  # Masked if present
    endpoint_url: Optional[str] = None  # Masked if present
    region: Optional[str] = None
    prefix: str
    public_base_url: Optional[str] = None


class StorageStatusResponse(BaseModel):
    """Storage status response (DEV ONLY - detailed diagnostics)"""
    storage_enabled: bool
    provider: str
    bucket: Optional[str] = None
    endpoint_url: Optional[str] = None
    region: Optional[str] = None
    public_base_url: Optional[str] = None
    presign_expires_seconds: int
    key_prefix: str
    reason_disabled: Optional[str] = None


def mask_sensitive(value: str, show_chars: int = 4) -> str:
    """Mask sensitive string, showing only first N chars"""
    if not value or len(value) <= show_chars:
        return "***"
    return f"{value[:show_chars]}..."


@router.get(
    "/system/storage",
    response_model=StorageInfoResponse,
    summary="Get storage configuration status",
    description="Get storage (S3/R2) configuration status. Requires ADMIN role. Never returns secrets.",
)
async def get_storage_info(
    principal: Principal = Depends(require_admin_role()),
) -> StorageInfoResponse:
    """Get storage configuration information"""
    return StorageInfoResponse(
        enabled=settings.storage_enabled,
        bucket=mask_sensitive(settings.S3_BUCKET) if settings.S3_BUCKET else None,
        endpoint_url=mask_sensitive(settings.S3_ENDPOINT_URL) if settings.S3_ENDPOINT_URL else None,
        region=settings.S3_REGION if settings.S3_REGION else None,
        prefix=settings.S3_KEY_PREFIX,
        public_base_url=settings.S3_PUBLIC_BASE_URL if settings.S3_PUBLIC_BASE_URL else None,
    )


@router.get(
    "/system/storage-status",
    response_model=StorageStatusResponse,
    summary="Get detailed storage status (DEV ONLY)",
    description="Get detailed storage (S3/R2) configuration status with diagnostics. DEV ONLY - requires DEV_MODE=True. Requires ADMIN role. Never returns secrets.",
)
async def get_storage_status(
    principal: Principal = Depends(require_admin_role()),
) -> StorageStatusResponse:
    """Get detailed storage status (DEV ONLY)"""
    # Only allow in dev mode or development/local environment
    env_lower = settings.ENV.lower()
    if not (settings.DEV_MODE or env_lower in ["local", "development", "dev"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NOT_FOUND"
        )
    
    # Get reason_disabled if storage is not enabled
    reason_disabled = settings.get_storage_disabled_reason()
    
    return StorageStatusResponse(
        storage_enabled=settings.storage_enabled,
        provider=settings.STORAGE_PROVIDER,
        bucket=settings.S3_BUCKET if settings.S3_BUCKET else None,
        endpoint_url=settings.S3_ENDPOINT_URL if settings.S3_ENDPOINT_URL else None,
        region=settings.S3_REGION if settings.S3_REGION else None,
        public_base_url=settings.S3_PUBLIC_BASE_URL if settings.S3_PUBLIC_BASE_URL else None,
        presign_expires_seconds=settings.S3_PRESIGN_EXPIRES_SECONDS,
        key_prefix=settings.S3_KEY_PREFIX,
        reason_disabled=reason_disabled,
    )

