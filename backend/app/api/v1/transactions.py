"""
Transactions API endpoints - READ-ONLY
"""

from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.infrastructure.database import get_db
from app.core.transactions.models import Transaction, TransactionType, TransactionStatus
from app.core.ledger.models import LedgerEntry, Operation
from app.core.accounts.models import Account, AccountType
from app.schemas.wallet import TransactionListItem

from app.auth.dependencies import require_user_role, get_user_id_from_principal
from app.auth.oidc import Principal

router = APIRouter()


def _compute_transaction_amount(
    db: Session,
    transaction_id: UUID,
    user_id: UUID,
    currency: str,
) -> Decimal:
    """
    Compute transaction amount by summing ledger entries affecting user wallet.
    
    Only includes ledger entries for user's wallet accounts (not INTERNAL_OMNIBUS).
    """
    # Get user's wallet account IDs for this currency
    wallet_accounts = db.query(Account).filter(
        Account.user_id == user_id,
        Account.currency == currency,
        Account.account_type.in_([
            AccountType.WALLET_AVAILABLE,
            AccountType.WALLET_BLOCKED,
            AccountType.WALLET_LOCKED,
        ])
    ).all()
    
    wallet_account_ids = [acc.id for acc in wallet_accounts]
    
    if not wallet_account_ids:
        return Decimal('0')
    
    # Get all operations for this transaction
    operations = db.query(Operation).filter(
        Operation.transaction_id == transaction_id
    ).all()
    
    operation_ids = [op.id for op in operations]
    
    if not operation_ids:
        return Decimal('0')
    
    # Sum ledger entries for user wallet accounts in this transaction's operations
    result = db.query(
        func.coalesce(func.sum(LedgerEntry.amount), Decimal('0'))
    ).filter(
        LedgerEntry.operation_id.in_(operation_ids),
        LedgerEntry.account_id.in_(wallet_account_ids),
    ).scalar()
    
    return Decimal(str(result)) if result is not None else Decimal('0')


@router.get(
    "/transactions",
    response_model=List[TransactionListItem],
    summary="Get transaction history",
    description="Get transaction history for authenticated user. READ-ONLY endpoint. Requires USER role.",
)
async def get_transactions(
    type: Optional[str] = Query(default=None, description="Filter by transaction type (DEPOSIT, WITHDRAWAL, INVESTMENT)"),
    status: Optional[str] = Query(default=None, description="Filter by transaction status"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of transactions to return"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role),
) -> List[TransactionListItem]:
    """
    Get transaction history for authenticated user.
    
    Returns transactions ordered by created_at DESC.
    
    Rules:
    - amount = sum of ledger entries for this transaction affecting user wallet
    - Do NOT expose internal operations
    - Do NOT expose compliance reasons
    
    READ-ONLY: No side effects, no mutations.
    
    Requires authentication (Bearer token) with USER role.
    """
    user_id = get_user_id_from_principal(principal)
    
    # Build query
    query = db.query(Transaction).filter(
        Transaction.user_id == user_id
    )
    
    # Apply filters
    if type:
        try:
            transaction_type = TransactionType[type.upper()]
            query = query.filter(Transaction.type == transaction_type)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid transaction type: {type}")
    
    if status:
        try:
            transaction_status = TransactionStatus[status.upper()]
            query = query.filter(Transaction.status == transaction_status)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid transaction status: {status}")
    
    # Order and limit
    transactions = query.order_by(Transaction.created_at.desc()).limit(limit).all()
    
    # Build response
    result = []
    for txn in transactions:
        # Determine currency from first operation's ledger entry (or default to AED)
        currency = "AED"  # Default
        operations = db.query(Operation).filter(Operation.transaction_id == txn.id).limit(1).all()
        if operations:
            ledger_entry = db.query(LedgerEntry).filter(
                LedgerEntry.operation_id == operations[0].id
            ).first()
            if ledger_entry:
                currency = ledger_entry.currency
        
        amount = _compute_transaction_amount(db, txn.id, user_id, currency)
        
        result.append(TransactionListItem(
            transaction_id=str(txn.id),
            type=txn.type.value,
            status=txn.status.value,
            amount=str(amount),
            currency=currency,
            created_at=txn.created_at.isoformat() + "Z",
        ))
    
    return result
