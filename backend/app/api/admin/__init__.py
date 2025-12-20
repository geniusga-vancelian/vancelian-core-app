"""
Admin API routes - INTERNAL ONLY
"""

from fastapi import APIRouter
from app.infrastructure.settings import get_settings
from app.api.admin.compliance import router as compliance_router
from app.api.admin.users import router as users_router
from app.api.admin.transactions import router as transactions_router
from app.api.admin.offers import router as offers_router
from app.api.admin.offers_media import router as offers_media_router
from app.api.admin.system import router as system_router
from app.api.admin.debug import router as debug_router

settings = get_settings()
router = APIRouter(prefix=settings.ADMIN_V1_PREFIX, tags=["admin-v1"])

# Register admin routers
router.include_router(compliance_router)
router.include_router(users_router, tags=["admin-users"])
router.include_router(transactions_router, tags=["admin-transactions"])
router.include_router(offers_router, tags=["admin-offers"])
router.include_router(offers_media_router, tags=["admin-offers-media"])
router.include_router(system_router, tags=["admin-system"])
router.include_router(debug_router, tags=["admin-debug"])
