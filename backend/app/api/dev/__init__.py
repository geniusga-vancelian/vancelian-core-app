"""
DEV-ONLY API endpoints for local development and testing
"""

from fastapi import APIRouter
from app.infrastructure.settings import get_settings

settings = get_settings()
router = APIRouter(prefix="/dev/v1", tags=["dev"])

# Import dev endpoints
from app.api.dev.tokens import router as tokens_router
from app.api.dev.bootstrap import router as bootstrap_router
from app.api.dev.webhooks import router as webhooks_router
from app.api.dev.e2e import router as e2e_router

router.include_router(tokens_router)
router.include_router(bootstrap_router)
router.include_router(webhooks_router)
router.include_router(e2e_router)

