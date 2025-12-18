"""
Investment API endpoints - USER-facing
"""

import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.core.transactions.models import Transaction, TransactionType, TransactionStatus
from app.core.accounts.models import Account, AccountType
from app.core.security.models import Role
from app.schemas.investments import CreateInvestmentRequest, CreateInvestmentResponse
from app.services.fund_services import (
    lock_funds_for_investment,
    InsufficientBalanceError,
    ValidationError,
)
from app.services.wallet_helpers import get_account_balance, ensure_wallet_accounts
from app.services.transaction_engine import recompute_transaction_status
from app.auth.dependencies import require_user_role, get_user_id_from_principal
from app.auth.oidc import Principal
from app.utils.metrics import record_investment_action

logger = logging.getLogger(__name__)

router = APIRouter()


def validate_offer_exists(offer_id: UUID) -> bool:
    """
    Validate that investment offer exists.
    
    TODO: Implement actual offer validation against investment offers database.
    For now, this is a stub that accepts all UUIDs.
    """
    # TODO: Query investment offers table to verify offer exists and is available
    # For now, stub accepts all valid UUIDs
    return True


@router.post(
    "/investments",
    response_model=CreateInvestmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create investment intent",
    description="Lock funds for investment. Funds move from AVAILABLE to LOCKED compartment. Requires USER role.",
)
async def create_investment(
    request: CreateInvestmentRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role),
) -> CreateInvestmentResponse:
    """
    Create investment intent and lock funds.
    
    This endpoint:
    1. Validates offer exists (stub for now)
    2. Validates sufficient available balance
    3. Creates Transaction (type=INVESTMENT, status=INITIATED)
    4. Calls lock_funds_for_investment() to move funds AVAILABLE → LOCKED
    5. Triggers Transaction Status Engine recompute
    6. Creates AuditLog entry
    
    Access: USER role only.
    
    Validation:
    - Amount must be > 0
    - Sufficient available_balance
    - Offer must exist (stub validation)
    
    Flow:
    - Transaction created: type=INVESTMENT, status=INITIATED
    - Funds locked: AVAILABLE → LOCKED
    - Status updated: INITIATED → LOCKED
    
    Requires authentication (Bearer token) with USER role.
    """
    user_id = get_user_id_from_principal(principal)
    
    # Validate offer exists (stub)
    if not validate_offer_exists(request.offer_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investment offer {request.offer_id} not found"
        )
    
    # Ensure wallet accounts exist
    wallet_accounts = ensure_wallet_accounts(db, user_id, request.currency)
    available_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
    
    # Check available balance
    available_balance = get_account_balance(db, available_account_id)
    if available_balance < request.amount:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Insufficient available balance: {available_balance} < {request.amount}"
        )
    
    # Create Transaction
    transaction = Transaction(
        user_id=user_id,
        type=TransactionType.INVESTMENT,
        status=TransactionStatus.INITIATED,  # Will be updated to LOCKED by Transaction Status Engine
        metadata={
            "offer_id": str(request.offer_id),
            "currency": request.currency,
            "reason": request.reason,
        },
    )
    db.add(transaction)
    db.flush()  # Get transaction.id
    
    try:
        # Lock funds for investment
        operation = lock_funds_for_investment(
            db=db,
            user_id=user_id,
            currency=request.currency,
            amount=request.amount,
            transaction_id=transaction.id,
            reason=request.reason,
        )
        
        # Recompute transaction status (should be LOCKED now)
        new_status = recompute_transaction_status(
            db=db,
            transaction_id=transaction.id,
        )
        
        # Record metrics
        record_investment_action()
        
        logger.info(
            f"Investment created: transaction_id={transaction.id}, "
            f"offer_id={request.offer_id}, amount={request.amount}, "
            f"status={new_status.value}, user_id={user_id}"
        )
        
        return CreateInvestmentResponse(
            transaction_id=str(transaction.id),
            status=new_status.value,
        )
        
    except InsufficientBalanceError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except ValidationError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        logger.error(
            f"Error creating investment: user_id={user_id}, offer_id={request.offer_id}, "
            f"error={str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing investment request"
        )
