"""
Vesting service - Release AVENIR vesting lots
"""

from decimal import Decimal
from datetime import date, datetime, timezone
from uuid import UUID, uuid4
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.core.vaults.models import VestingLot, VestingLotStatus
from app.core.ledger.models import Operation, OperationType, OperationStatus, LedgerEntry, LedgerEntryType
from app.core.accounts.models import Account, AccountType
from app.core.accounts.wallet_locks import WalletLock, LockReason, LockStatus
from app.services.wallet_helpers import ensure_wallet_accounts, get_account_balance
from app.utils.ledger_validator import validate_double_entry_invariant


class VestingError(Exception):
    """Base exception for vesting operations"""
    pass


class VestingReleaseError(VestingError):
    """Raised when vesting release fails"""
    pass


def normalize_to_utc_midnight(d: date) -> date:
    """Normalize a date to UTC midnight (already a date, return as-is)"""
    return d


def release_avenir_vesting_lots(
    db: Session,
    *,
    as_of_date: Optional[date] = None,
    currency: str = "AED",
    dry_run: bool = False,
    trace_id: Optional[str] = None,
    max_lots: int = 1000,
) -> Dict[str, Any]:
    """
    Release mature AVENIR vesting lots.
    
    This function is idempotent and replayable:
    - Idempotent: Same trace_id won't process the same lot twice
    - Replayable: Different trace_id can process remaining lots after errors
    
    Args:
        db: Database session
        as_of_date: Date to use for maturity check (default: today UTC)
        currency: Currency filter (default: "AED")
        dry_run: If True, simulate without committing (default: False)
        trace_id: Unique trace ID for idempotence (default: generated UUID)
        max_lots: Maximum lots to process in one run (default: 1000)
    
    Returns:
        Dict with summary statistics:
        - matured_found: Number of mature lots found
        - executed_count: Number of lots successfully released
        - executed_amount: Total amount released (Decimal as string)
        - skipped_count: Number of lots skipped (already released or not mature)
        - errors_count: Number of errors encountered
        - errors: List of error messages
        - trace_id: Trace ID used for this run
        - as_of_date: Date used for maturity check (ISO format)
    """
    # Normalize date
    if as_of_date is None:
        as_of_date = datetime.now(timezone.utc).date()
    else:
        as_of_date = normalize_to_utc_midnight(as_of_date)
    
    # Generate trace_id if not provided
    if trace_id is None:
        trace_id = str(uuid4())
    
    stats = {
        'matured_found': 0,
        'executed_count': 0,
        'executed_amount': Decimal('0.00'),
        'skipped_count': 0,
        'errors_count': 0,
        'errors': [],
        'trace_id': trace_id,
        'as_of_date': as_of_date.isoformat(),
    }
    
    try:
        # Query mature lots
        # SELECT ... FOR UPDATE SKIP LOCKED for concurrency safety
        mature_lots = db.query(VestingLot).filter(
            and_(
                VestingLot.vault_code == 'AVENIR',
                VestingLot.release_day <= as_of_date,
                VestingLot.status == VestingLotStatus.VESTED.value,
                VestingLot.released_amount < VestingLot.amount,
                VestingLot.currency == currency,
            )
        ).order_by(
            VestingLot.release_day.asc(),
            VestingLot.created_at.asc(),
        ).limit(max_lots).with_for_update(skip_locked=True).all()
        
        stats['matured_found'] = len(mature_lots)
        
        # Process each lot
        for lot in mature_lots:
            try:
                # Check idempotence: skip if already processed with this trace_id
                if lot.release_job_trace_id == trace_id:
                    stats['skipped_count'] += 1
                    continue
                
                # Double-check maturity
                if lot.release_day > as_of_date:
                    stats['skipped_count'] += 1
                    continue
                
                # Double-check status
                if lot.status != VestingLotStatus.VESTED.value:
                    stats['skipped_count'] += 1
                    continue
                
                # Calculate release amount (full release for V1)
                release_amount = lot.amount - lot.released_amount
                
                if release_amount <= 0:
                    stats['skipped_count'] += 1
                    continue
                
                # Ensure wallet accounts exist
                wallet_accounts = ensure_wallet_accounts(db, lot.user_id, currency)
                locked_account_id = wallet_accounts[AccountType.WALLET_LOCKED.value]
                available_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
                
                # Check locked balance (should be >= release_amount)
                locked_balance = get_account_balance(db, locked_account_id)
                if locked_balance < release_amount:
                    error_msg = f"Insufficient locked balance for lot {lot.id}: {locked_balance} < {release_amount}"
                    stats['errors'].append(error_msg)
                    stats['errors_count'] += 1
                    continue
                
                # Create operation
                operation = Operation(
                    transaction_id=None,
                    type=OperationType.VAULT_VESTING_RELEASE,
                    status=OperationStatus.COMPLETED,
                    idempotency_key=None,
                    operation_metadata={
                        'vault_code': 'AVENIR',
                        'vault_id': str(lot.vault_id),
                        'vesting_lot_id': str(lot.id),
                        'release_date': as_of_date.isoformat(),
                        'trace_id': trace_id,
                        'release_amount': str(release_amount),
                        'currency': currency,
                    },
                )
                db.add(operation)
                db.flush()  # CRITICAL: Get operation.id
                
                # Create ledger entries (double-entry)
                # DEBIT WALLET_LOCKED (user)
                debit_entry = LedgerEntry(
                    operation_id=operation.id,
                    account_id=locked_account_id,
                    amount=-release_amount,  # Negative for DEBIT
                    currency=currency,
                    entry_type=LedgerEntryType.DEBIT,
                )
                
                # CREDIT WALLET_AVAILABLE (user)
                credit_entry = LedgerEntry(
                    operation_id=operation.id,
                    account_id=available_account_id,
                    amount=release_amount,  # Positive for CREDIT
                    currency=currency,
                    entry_type=LedgerEntryType.CREDIT,
                )
                
                db.add(debit_entry)
                db.add(credit_entry)
                db.flush()
                
                # Validate double-entry invariant
                if not validate_double_entry_invariant(db, operation.id):
                    db.rollback()
                    error_msg = f"Double-entry violation for lot {lot.id}"
                    stats['errors'].append(error_msg)
                    stats['errors_count'] += 1
                    continue
                
                # Update lot
                lot.released_amount += release_amount
                lot.last_released_at = datetime.now(timezone.utc)
                lot.last_release_operation_id = operation.id
                lot.release_job_trace_id = trace_id
                lot.release_job_run_at = datetime.now(timezone.utc)
                
                if lot.released_amount >= lot.amount:
                    lot.status = VestingLotStatus.RELEASED.value
                
                # Update wallet_lock if exists (for Wallet Matrix coherence)
                wallet_lock = db.query(WalletLock).filter(
                    WalletLock.operation_id == lot.source_operation_id,
                    WalletLock.reason == LockReason.VAULT_AVENIR_VESTING.value,
                    WalletLock.status == LockStatus.ACTIVE.value,
                ).first()
                
                if wallet_lock:
                    if wallet_lock.amount <= release_amount:
                        # Full release
                        wallet_lock.status = LockStatus.RELEASED.value
                        wallet_lock.released_at = datetime.now(timezone.utc)
                    else:
                        # Partial release: create new lock for remaining
                        remaining_lock_amount = wallet_lock.amount - release_amount
                        wallet_lock.status = LockStatus.RELEASED.value
                        wallet_lock.released_at = datetime.now(timezone.utc)
                        
                        new_lock = WalletLock(
                            user_id=lot.user_id,
                            currency=currency,
                            amount=remaining_lock_amount,
                            reason=LockReason.VAULT_AVENIR_VESTING.value,
                            reference_type='VAULT',
                            reference_id=lot.vault_id,
                            status=LockStatus.ACTIVE.value,
                            operation_id=None,  # No source operation for partial lock
                        )
                        db.add(new_lock)
                
                # Commit transaction (or rollback if dry_run)
                if dry_run:
                    db.rollback()
                else:
                    db.commit()
                
                stats['executed_count'] += 1
                stats['executed_amount'] += release_amount
                
            except Exception as e:
                db.rollback()
                error_msg = f"Error processing lot {lot.id}: {str(e)}"
                stats['errors'].append(error_msg)
                stats['errors_count'] += 1
                # Continue with next lot (fail-soft)
        
        # Convert executed_amount to string for JSON serialization
        stats['executed_amount'] = str(stats['executed_amount'].quantize(Decimal('0.01')))
        
        return stats
    
    except Exception as e:
        db.rollback()
        error_msg = f"Critical error in release_avenir_vesting_lots: {str(e)}"
        stats['errors'].append(error_msg)
        stats['errors_count'] += 1
        raise VestingReleaseError(error_msg) from e

