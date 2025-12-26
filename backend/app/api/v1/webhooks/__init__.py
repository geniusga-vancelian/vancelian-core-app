"""
Webhook simulation endpoints (DEV ONLY)
"""

from fastapi import APIRouter
from app.api.v1.webhooks.zandbank import router as zandbank_router

router = APIRouter(prefix="/webhooks/zandbank", tags=["webhooks-sim"])

# Register webhook simulation routers
router.include_router(zandbank_router)


