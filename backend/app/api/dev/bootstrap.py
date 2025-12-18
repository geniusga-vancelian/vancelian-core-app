"""
DEV-ONLY endpoints for user bootstrap
⚠️ These endpoints are ONLY available when DEV_MODE=true
"""

import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.infrastructure.settings import get_settings
from app.infrastructure.database import get_db
from app.core.users.models import User, UserStatus
from app.core.accounts.models import AccountType
from app.services.wallet_helpers import ensure_wallet_accounts
from app.utils.trace_id import trace_id_context

router = APIRouter(prefix="/bootstrap", tags=["dev-bootstrap"])
settings = get_settings()


class BootstrapUserRequest(BaseModel):
    """Request body for user bootstrap"""
    email: Optional[str] = "user@vancelian.dev"
    sub: Optional[str] = "11111111-1111-1111-1111-111111111111"  # external_subject
    currency: Optional[str] = "AED"


class BootstrapUserResponse(BaseModel):
    """Response for user bootstrap"""
    user_id: str
    email: str
    currency: str
    accounts: dict[str, str]  # account_type -> account_id


@router.post(
    "/user",
    response_model=BootstrapUserResponse,
    summary="Bootstrap test user (DEV-ONLY)",
    description="""
    **DEV-ONLY**: Create or get a test user with default wallet accounts.
    
    This endpoint is ONLY available when DEV_MODE=true.
    ⚠️ Never expose this endpoint in production!
    
    Behavior:
    - Idempotent: If user exists by email OR external_subject, returns existing user
    - Creates default wallet accounts for the specified currency:
      - WALLET_AVAILABLE
      - WALLET_BLOCKED_COMPLIANCE (same as WALLET_BLOCKED)
      - WALLET_LOCKED_INVESTMENT (same as WALLET_LOCKED)
    """,
)
async def bootstrap_user(
    request: BootstrapUserRequest = BootstrapUserRequest(),
    db: Session = Depends(get_db),
) -> BootstrapUserResponse:
    """
    Bootstrap a test user with default wallet accounts.
    """
    # Security check: Only allow if DEV_MODE is enabled
    if not settings.DEV_MODE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,  # 404 to hide endpoint existence
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Endpoint not found",
                    "trace_id": trace_id_context.get(),
                }
            },
        )
    
    email = request.email or "user@vancelian.dev"
    external_subject = request.sub or "11111111-1111-1111-1111-111111111111"
    currency = request.currency or "AED"
    
    # Try to find existing user by email
    user = db.query(User).filter(User.email == email).first()
    
    # If not found by email, try by external_subject
    if not user:
        user = db.query(User).filter(User.external_subject == external_subject).first()
    
    # Create user if not found
    if not user:
        user = User(
            email=email,
            status=UserStatus.ACTIVE,
            external_subject=external_subject,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Ensure wallet accounts exist
    wallet_accounts = ensure_wallet_accounts(db, user.id, currency)
    db.commit()
    
    # Map account types to IDs for response
    accounts = {
        "available_account_id": str(wallet_accounts[AccountType.WALLET_AVAILABLE.value]),
        "blocked_account_id": str(wallet_accounts[AccountType.WALLET_BLOCKED.value]),
        "locked_account_id": str(wallet_accounts[AccountType.WALLET_LOCKED.value]),
    }
    
    return BootstrapUserResponse(
        user_id=str(user.id),
        email=user.email,
        currency=currency,
        accounts=accounts,
    )

