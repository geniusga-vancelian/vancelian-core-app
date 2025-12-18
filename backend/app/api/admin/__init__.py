"""
Admin API routes - INTERNAL ONLY
"""

from fastapi import APIRouter
from app.infrastructure.settings import get_settings
from app.api.admin.compliance import router as compliance_router

settings = get_settings()
router = APIRouter(prefix=settings.ADMIN_V1_PREFIX, tags=["admin-v1"])

# Register admin routers
router.include_router(compliance_router)
