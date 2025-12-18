"""
Transaction Status Engine - Derives Transaction.status from completed Operations
"""

from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.transactions.models import Transaction, TransactionType, TransactionStatus
from app.core.ledger.models import Operation, OperationType, OperationStatus


def recompute_transaction_status(
    *,
    db: Session,
    transaction_id: UUID,
) -> TransactionStatus:
    """
    Recompute and update Transaction.status based on completed Operations.
    
    Rules (deterministic mapping):
    
    TransactionType = DEPOSIT:
    - INITIATED: No completed Operation yet
    - COMPLIANCE_REVIEW: Operation DEPOSIT_AED completed, but no RELEASE_FUNDS yet
    - AVAILABLE: Operation RELEASE_FUNDS completed
    - FAILED: Any Operation FAILED
    - CANCELLED: Explicit cancellation only (future)
    
    This function is:
    - Idempotent: Safe to call multiple times
    - Deterministic: Same Operations → same status
    - Side-effect free: Only updates Transaction.status
    
    Returns the computed TransactionStatus.
    """
    # Load Transaction
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id
    ).first()
    
    if not transaction:
        raise ValueError(f"Transaction {transaction_id} not found")
    
    # Load all Operations for this Transaction
    operations = db.query(Operation).filter(
        Operation.transaction_id == transaction_id
    ).all()
    
    # Determine status based on TransactionType and Operations
    computed_status = _compute_status(transaction.type, operations)
    
    # Update Transaction.status ONLY if changed
    if transaction.status != computed_status:
        transaction.status = computed_status
        db.commit()
    
    return computed_status


def _compute_status(
    transaction_type: TransactionType,
    operations: list[Operation],
) -> TransactionStatus:
    """
    Compute TransactionStatus from TransactionType and Operations.
    
    Rules are explicitly defined per TransactionType.
    """
    if transaction_type == TransactionType.DEPOSIT:
        return _compute_deposit_status(operations)
    elif transaction_type == TransactionType.WITHDRAWAL:
        return _compute_withdrawal_status(operations)
    elif transaction_type == TransactionType.INVESTMENT:
        return _compute_investment_status(operations)
    else:
        # Default: return current status or INITIATED
        return TransactionStatus.INITIATED


def _compute_deposit_status(operations: list[Operation]) -> TransactionStatus:
    """
    Compute status for DEPOSIT transaction.
    
    Rules:
    - INITIATED: No completed Operation yet
    - COMPLIANCE_REVIEW: DEPOSIT_AED completed, but no RELEASE_FUNDS or REVERSAL yet
    - AVAILABLE: RELEASE_FUNDS completed (funds released after compliance review)
    - FAILED: REVERSAL_DEPOSIT completed (deposit rejected)
    - FAILED: Any Operation FAILED
    - CANCELLED: Explicit cancellation (future)
    
    Note: Once FAILED, transaction cannot become AVAILABLE.
    """
    # Check for REVERSAL_DEPOSIT completion (deposit rejected) - highest priority
    has_reversal_completed = any(
        op.type == OperationType.REVERSAL_DEPOSIT
        and op.status == OperationStatus.COMPLETED
        for op in operations
    )
    if has_reversal_completed:
        return TransactionStatus.FAILED
    
    # Check for FAILED Operations
    has_failed = any(op.status == OperationStatus.FAILED for op in operations)
    if has_failed:
        return TransactionStatus.FAILED
    
    # Check for CANCELLED Operations
    has_cancelled = any(op.status == OperationStatus.CANCELLED for op in operations)
    if has_cancelled:
        return TransactionStatus.CANCELLED
    
    # Check for RELEASE_FUNDS completion (funds available)
    has_release_completed = any(
        op.type == OperationType.RELEASE_FUNDS
        and op.status == OperationStatus.COMPLETED
        for op in operations
    )
    if has_release_completed:
        return TransactionStatus.AVAILABLE
    
    # Check for DEPOSIT_AED completion (in compliance review)
    has_deposit_completed = any(
        op.type == OperationType.DEPOSIT_AED
        and op.status == OperationStatus.COMPLETED
        for op in operations
    )
    if has_deposit_completed:
        return TransactionStatus.COMPLIANCE_REVIEW
    
    # Default: INITIATED (no completed operations yet)
    return TransactionStatus.INITIATED


def _compute_withdrawal_status(operations: list[Operation]) -> TransactionStatus:
    """
    Compute status for WITHDRAWAL transaction.
    
    Rules (simplified for now):
    - INITIATED: No completed Operation yet
    - FAILED: Any Operation FAILED
    - AVAILABLE: Withdrawal completed (future)
    - CANCELLED: Explicit cancellation (future)
    """
    # Check for FAILED Operations
    has_failed = any(op.status == OperationStatus.FAILED for op in operations)
    if has_failed:
        return TransactionStatus.FAILED
    
    # Check for CANCELLED Operations
    has_cancelled = any(op.status == OperationStatus.CANCELLED for op in operations)
    if has_cancelled:
        return TransactionStatus.CANCELLED
    
    # TODO: Add withdrawal completion logic when implemented
    # For now, return INITIATED
    return TransactionStatus.INITIATED


def _compute_investment_status(operations: list[Operation]) -> TransactionStatus:
    """
    Compute status for INVESTMENT transaction.
    
    Rules:
    - INITIATED: No completed Operation yet
    - LOCKED: Operation INVEST_EXCLUSIVE completed (funds locked)
    - FAILED: Any Operation FAILED
    - CANCELLED: Explicit cancellation (future)
    """
    # Check for FAILED Operations
    has_failed = any(op.status == OperationStatus.FAILED for op in operations)
    if has_failed:
        return TransactionStatus.FAILED
    
    # Check for CANCELLED Operations
    has_cancelled = any(op.status == OperationStatus.CANCELLED for op in operations)
    if has_cancelled:
        return TransactionStatus.CANCELLED
    
    # Check for INVEST_EXCLUSIVE completion (funds locked for investment)
    has_invest_completed = any(
        op.type == OperationType.INVEST_EXCLUSIVE
        and op.status == OperationStatus.COMPLETED
        for op in operations
    )
    if has_invest_completed:
        # Investment operation completed - funds locked
        # Status is LOCKED (funds are locked for investment, non-withdrawable)
        return TransactionStatus.LOCKED
    
    # Default: INITIATED
    return TransactionStatus.INITIATED

