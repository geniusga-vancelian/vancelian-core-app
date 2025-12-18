"""
Ledger invariant validation utilities
"""

import logging
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.ledger.models import LedgerEntry
from app.utils.metrics import record_ledger_invariant_violation

logger = logging.getLogger(__name__)


def validate_double_entry_invariant(
    db: Session,
    operation_id: str,
) -> bool:
    """
    Validate double-entry accounting invariant for an operation.
    
    Invariant: Sum of CREDIT entries == Sum of DEBIT entries (absolute values)
    
    Args:
        db: Database session
        operation_id: Operation ID to validate
    
    Returns:
        True if invariant holds, False otherwise
    
    Side effects:
        Records metric if violation detected
    """
    # Get all ledger entries for this operation
    entries = db.query(LedgerEntry).filter(
        LedgerEntry.operation_id == operation_id
    ).all()
    
    if not entries:
        # No entries - invariant holds trivially
        return True
    
    # Calculate sum of credits (positive amounts)
    credit_sum = Decimal('0')
    debit_sum = Decimal('0')
    
    for entry in entries:
        if entry.entry_type.value == "CREDIT":
            credit_sum += abs(entry.amount)
        elif entry.entry_type.value == "DEBIT":
            debit_sum += abs(entry.amount)
    
    # Invariant: credits == debits
    if credit_sum != debit_sum:
        logger.error(
            f"Double-entry invariant violation: operation_id={operation_id}, "
            f"credit_sum={credit_sum}, debit_sum={debit_sum}"
        )
        record_ledger_invariant_violation()
        return False
    
    return True


def validate_operation_balance(
    db: Session,
    operation_id: str,
    expected_balance: Decimal = Decimal('0'),
) -> bool:
    """
    Validate that operation entries sum to expected balance.
    
    Args:
        db: Database session
        operation_id: Operation ID to validate
        expected_balance: Expected sum (default: 0 for double-entry)
    
    Returns:
        True if balance matches, False otherwise
    """
    result = db.query(
        func.coalesce(func.sum(LedgerEntry.amount), Decimal('0'))
    ).filter(
        LedgerEntry.operation_id == operation_id
    ).scalar()
    
    actual_balance = Decimal(str(result)) if result is not None else Decimal('0')
    
    if actual_balance != expected_balance:
        logger.error(
            f"Operation balance violation: operation_id={operation_id}, "
            f"expected={expected_balance}, actual={actual_balance}"
        )
        record_ledger_invariant_violation()
        return False
    
    return True

