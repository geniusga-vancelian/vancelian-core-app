"""
Admin API routes - INTERNAL ONLY
"""

from fastapi import APIRouter
from app.infrastructure.settings import get_settings
from app.api.admin.compliance import router as compliance_router
from app.api.admin.users import router as users_router
from app.api.admin.transactions import router as transactions_router

settings = get_settings()
router = APIRouter(prefix=settings.ADMIN_V1_PREFIX, tags=["admin-v1"])

# Register admin routers
router.include_router(compliance_router)
router.include_router(users_router, tags=["admin-users"])
router.include_router(transactions_router, tags=["admin-transactions"])
