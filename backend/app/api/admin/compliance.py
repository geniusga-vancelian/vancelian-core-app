"""
Compliance API endpoints - INTERNAL ONLY
"""

import logging
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.core.transactions.models import Transaction, TransactionType, TransactionStatus
from app.core.ledger.models import Operation, OperationType, OperationStatus, LedgerEntry, LedgerEntryType
from app.core.accounts.models import Account, AccountType
from app.core.security.models import Role
from app.schemas.compliance import (
    ReleaseFundsRequest,
    ReleaseFundsResponse,
    RejectDepositRequest,
    RejectDepositResponse,
)
from app.services.fund_services import (
    release_compliance_funds,
    reject_deposit,
    InsufficientBalanceError,
    ValidationError,
)
from app.services.wallet_helpers import get_account_balance
from app.services.transaction_engine import recompute_transaction_status
from app.auth.dependencies import require_compliance_or_ops, get_user_id_from_principal
from app.auth.oidc import Principal
from app.utils.metrics import record_compliance_action

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/compliance/release-funds",
    response_model=ReleaseFundsResponse,
    status_code=status.HTTP_200_OK,
    summary="Release compliance-blocked funds",
    description="Release funds from BLOCKED to AVAILABLE after compliance review. INTERNAL ONLY. Requires COMPLIANCE or OPS role.",
)
async def release_funds(
    request: ReleaseFundsRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_compliance_or_ops),
) -> ReleaseFundsResponse:
    """
    Release funds from COMPLIANCE_REVIEW status to AVAILABLE.
    
    This endpoint:
    1. Validates transaction exists and is in correct state
    2. Validates amount <= blocked balance
    3. Calls release_compliance_funds() service
    4. Triggers Transaction Status Engine recompute
    5. Creates AuditLog entry with reason
    
    Access: COMPLIANCE or OPS role only.
    
    Validation:
    - Transaction must exist
    - Transaction.type must be DEPOSIT
    - Transaction.status must be COMPLIANCE_REVIEW
    - Amount must be > 0
    - Amount must be <= blocked balance for transaction/user
    """
    actor_user_id = get_user_id_from_principal(principal)
    
    # Load transaction
    transaction = db.query(Transaction).filter(
        Transaction.id == request.transaction_id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {request.transaction_id} not found"
        )
    
    # Validate transaction type
    if transaction.type != TransactionType.DEPOSIT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Transaction type must be DEPOSIT, got {transaction.type.value}"
        )
    
    # Validate transaction status
    if transaction.status != TransactionStatus.COMPLIANCE_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transaction status must be COMPLIANCE_REVIEW, got {transaction.status.value}"
        )
    
    # Determine currency from transaction operations
    currency = "AED"  # Default
    operations = db.query(Operation).filter(
        Operation.transaction_id == transaction.id
    ).limit(1).all()
    
    if operations:
        # Get currency from first ledger entry
        from app.core.ledger.models import LedgerEntry
        ledger_entry = db.query(LedgerEntry).filter(
            LedgerEntry.operation_id == operations[0].id
        ).first()
        if ledger_entry:
            currency = ledger_entry.currency
    
    # Get blocked account balance for validation
    blocked_account = db.query(Account).filter(
        Account.user_id == transaction.user_id,
        Account.currency == currency,
        Account.account_type == AccountType.WALLET_BLOCKED,
    ).first()
    
    if not blocked_account:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No WALLET_BLOCKED account found for user {transaction.user_id} and currency {currency}"
        )
    
    blocked_balance = get_account_balance(db, blocked_account.id)
    
    # Validate amount <= blocked balance
    if request.amount > blocked_balance:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Amount {request.amount} exceeds blocked balance {blocked_balance}"
        )
    
    try:
        # Release funds (service handles AuditLog and Transaction Status Engine update)
        operation = release_compliance_funds(
            db=db,
            user_id=transaction.user_id,
            currency=currency,
            amount=request.amount,
            transaction_id=transaction.id,
            reason=request.reason,
            actor_user_id=actor_user_id,  # TODO: Get from authenticated user
        )
        
        # Recompute transaction status (should be AVAILABLE now)
        new_status = recompute_transaction_status(
            db=db,
            transaction_id=transaction.id,
        )
        
        # Record metrics
        record_compliance_action(action="release_funds")
        
        logger.info(
            f"Funds released: transaction_id={transaction.id}, "
            f"amount={request.amount}, new_status={new_status.value}, "
            f"actor_user_id={actor_user_id}"
        )
        
        return ReleaseFundsResponse(
            transaction_id=str(transaction.id),
            status=new_status.value,
        )
        
    except InsufficientBalanceError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            f"Error releasing funds: transaction_id={transaction.id}, error={str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing release funds request"
        )


@router.post(
    "/compliance/reject-deposit",
    response_model=RejectDepositResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject deposit transaction",
    description="Reject a deposit transaction by reversing it. Moves funds from BLOCKED back to INTERNAL_OMNIBUS. INTERNAL ONLY. Requires COMPLIANCE or OPS role.",
)
async def reject_deposit_transaction(
    request: RejectDepositRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_compliance_or_ops),
) -> RejectDepositResponse:
    """
    Reject a deposit transaction and reverse the funds.
    
    This endpoint:
    1. Validates transaction exists and is in correct state
    2. Computes blocked balance for transaction
    3. Calls reject_deposit() service to reverse funds
    4. Triggers Transaction Status Engine recompute
    5. Creates AuditLog entry with reason
    
    Access: COMPLIANCE or OPS role only.
    
    Validation:
    - Transaction must exist
    - Transaction.type must be DEPOSIT
    - Transaction.status must be COMPLIANCE_REVIEW
    - Reason is mandatory (audit trail)
    
    Flow:
    - Funds reversed: WALLET_BLOCKED → INTERNAL_OMNIBUS
    - Status updated: COMPLIANCE_REVIEW → FAILED
    - Ledger immutability preserved (new reversal entries created)
    """
    actor_user_id = get_user_id_from_principal(principal)
    
    # Load transaction
    transaction = db.query(Transaction).filter(
        Transaction.id == request.transaction_id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {request.transaction_id} not found"
        )
    
    # Validate transaction type
    if transaction.type != TransactionType.DEPOSIT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Transaction type must be DEPOSIT, got {transaction.type.value}"
        )
    
    # Validate transaction status
    if transaction.status != TransactionStatus.COMPLIANCE_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transaction status must be COMPLIANCE_REVIEW, got {transaction.status.value}"
        )
    
    # Determine currency and amount from transaction operations
    currency = "AED"  # Default
    amount = Decimal('0')
    
    # Find the original DEPOSIT_AED operation to get amount
    deposit_operation = db.query(Operation).filter(
        Operation.transaction_id == transaction.id,
        Operation.type == OperationType.DEPOSIT_AED,
        Operation.status == OperationStatus.COMPLETED,
    ).first()
    
    if not deposit_operation:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No completed DEPOSIT_AED operation found for this transaction"
        )
    
    # Get the blocked account credit amount from the original deposit
    blocked_ledger_entry = db.query(LedgerEntry).filter(
        LedgerEntry.operation_id == deposit_operation.id,
        LedgerEntry.entry_type == LedgerEntryType.CREDIT,
    ).first()
    
    if not blocked_ledger_entry:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not determine deposit amount from ledger entries"
        )
    
    currency = blocked_ledger_entry.currency
    amount = Decimal(str(blocked_ledger_entry.amount))  # Original credit amount (positive)
    
    try:
        # Reject deposit (service handles reversal, AuditLog, and Transaction Status Engine update)
        operation = reject_deposit(
            db=db,
            transaction_id=transaction.id,
            user_id=transaction.user_id,
            currency=currency,
            amount=amount,
            reason=request.reason,
            actor_user_id=actor_user_id,  # TODO: Get from authenticated user
        )
        
        # Recompute transaction status (should be FAILED now)
        new_status = recompute_transaction_status(
            db=db,
            transaction_id=transaction.id,
        )
        
        # Record metrics
        record_compliance_action(action="reject_deposit")
        
        logger.info(
            f"Deposit rejected: transaction_id={transaction.id}, "
            f"amount={amount}, new_status={new_status.value}, "
            f"actor_user_id={actor_user_id}, reason={request.reason}"
        )
        
        return RejectDepositResponse(
            transaction_id=str(transaction.id),
            status=new_status.value,
        )
        
    except InsufficientBalanceError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            f"Error rejecting deposit: transaction_id={transaction.id}, error={str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing reject deposit request"
        )

