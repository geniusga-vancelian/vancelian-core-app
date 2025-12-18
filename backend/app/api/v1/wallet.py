"""
Wallet API endpoints - READ-ONLY
"""

from decimal import Decimal
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.services.wallet_helpers import get_wallet_balances
from app.schemas.wallet import WalletBalanceResponse

from app.auth.dependencies import require_user_role, get_user_id_from_principal
from app.auth.oidc import Principal

router = APIRouter()


@router.get(
    "/wallet",
    response_model=WalletBalanceResponse,
    summary="Get wallet balances",
    description="Get wallet balances for authenticated user. READ-ONLY endpoint. Requires USER role.",
)
async def get_wallet(
    currency: str = Query(default="AED", description="ISO 4217 currency code"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role),
) -> WalletBalanceResponse:
    """
    Get wallet balances for all compartments.
    
    Returns balances for:
    - total_balance: Sum of all wallet compartments
    - available_balance: WALLET_AVAILABLE compartment
    - blocked_balance: WALLET_BLOCKED compartment
    - locked_balance: WALLET_LOCKED compartment
    
    READ-ONLY: No side effects, no mutations.
    
    Requires authentication (Bearer token) with USER role.
    """
    user_id = get_user_id_from_principal(principal)
    balances = get_wallet_balances(db, user_id, currency)
    return WalletBalanceResponse(
        currency=currency,
        total_balance=str(balances['total_balance']),
        available_balance=str(balances['available_balance']),
        blocked_balance=str(balances['blocked_balance']),
        locked_balance=str(balances['locked_balance']),
    )

