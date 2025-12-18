"""
Webhook endpoints - INTERNAL / BANK ONLY
"""

from fastapi import APIRouter
from app.infrastructure.settings import get_settings
from app.api.webhooks.zand import router as zand_router

settings = get_settings()
router = APIRouter(prefix=settings.WEBHOOKS_V1_PREFIX, tags=["webhooks-v1"])

# Register webhook routers
router.include_router(zand_router)
