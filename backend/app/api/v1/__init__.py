"""
API v1 routes - User-facing API
"""

from fastapi import APIRouter
from app.infrastructure.settings import get_settings
from app.api.v1.wallet import router as wallet_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.investments import router as investments_router

settings = get_settings()
router = APIRouter(prefix=settings.API_V1_PREFIX, tags=["api-v1"])

# Register sub-routers
router.include_router(wallet_router)
router.include_router(transactions_router)
router.include_router(investments_router)

