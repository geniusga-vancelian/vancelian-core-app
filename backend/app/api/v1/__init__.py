"""
API v1 routes - User-facing API
"""

from fastapi import APIRouter, Response
from app.infrastructure.settings import get_settings
from app.api.v1.wallet import router as wallet_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.investments import router as investments_router
from app.api.v1.offers import router as offers_router
from app.api.v1.auth import router as auth_router
from app.api.v1.me import router as me_router

settings = get_settings()
router = APIRouter(prefix=settings.API_V1_PREFIX, tags=["api-v1"])

# Safety net: Explicit OPTIONS handler for all /api/v1/* routes
# CORSMiddleware should handle this automatically, but this provides a fallback
@router.options("/{path:path}")
async def options_handler(path: str):
    """
    Handle OPTIONS preflight requests for all /api/v1/* routes.
    
    CORSMiddleware should handle this, but this provides a safety net.
    This route will only be hit if CORSMiddleware doesn't intercept.
    """
    return Response(status_code=200)

# Register sub-routers
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(me_router)
router.include_router(wallet_router)
router.include_router(transactions_router)
router.include_router(investments_router)
router.include_router(offers_router)

