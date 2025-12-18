"""
Fund movement services - Move funds between wallet compartments using Operations + LedgerEntries
"""

from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.accounts.models import Account, AccountType
from app.core.ledger.models import Operation, OperationType, OperationStatus, LedgerEntry, LedgerEntryType
from app.utils.ledger_validator import validate_double_entry_invariant
from app.core.compliance.models import AuditLog
from app.core.security.models import Role
from app.services.wallet_helpers import ensure_wallet_accounts, get_account_balance
from app.services.transaction_engine import recompute_transaction_status


class InsufficientBalanceError(Exception):
    """Raised when insufficient balance for operation"""
    pass


class ValidationError(Exception):
    """Raised when validation fails"""
    pass


def record_deposit_blocked(
    *,
    db: Session,
    user_id: UUID,
    currency: str,
    amount: Decimal,
    transaction_id: Optional[UUID] = None,
    idempotency_key: Optional[str] = None,
    provider_reference: Optional[str] = None,
) -> Operation:
    """
    Record a deposit into WALLET_BLOCKED compartment.
    
    Creates:
    - Operation (DEPOSIT_AED, COMPLETED)
    - LedgerEntries: CREDIT WALLET_BLOCKED, DEBIT INTERNAL_OMNIBUS
    - AuditLog
    
    Idempotency: If idempotency_key exists, returns existing operation.
    """
    # Validate amount
    if amount <= 0:
        raise ValidationError("Amount must be greater than 0")
    
    # Check idempotency
    if idempotency_key:
        existing = db.query(Operation).filter(
            Operation.idempotency_key == idempotency_key
        ).first()
        if existing:
            return existing
    
    # Ensure wallet accounts exist
    wallet_accounts = ensure_wallet_accounts(db, user_id, currency)
    blocked_account_id = wallet_accounts[AccountType.WALLET_BLOCKED.value]
    
    # Get or create INTERNAL_OMNIBUS account (system-wide, not user-specific)
    # Idempotent: create if not exists (DEV-friendly, safe in prod too)
    omnibus_account = db.query(Account).filter(
        Account.account_type == AccountType.INTERNAL_OMNIBUS,
        Account.currency == currency,
    ).first()
    
    if not omnibus_account:
        # Create INTERNAL_OMNIBUS account if it doesn't exist (idempotent)
        omnibus_account = Account(
            id=uuid4(),
            user_id=None,  # System account (no user)
            currency=currency,
            account_type=AccountType.INTERNAL_OMNIBUS,
        )
        db.add(omnibus_account)
        db.flush()  # Get account.id
    
    omnibus_account_id = omnibus_account.id
    
    # Create operation
    operation = Operation(
        transaction_id=transaction_id,
        type=OperationType.DEPOSIT_AED,
        status=OperationStatus.COMPLETED,
        idempotency_key=idempotency_key,
        metadata={
            'provider_reference': provider_reference,
            'currency': currency,
        } if provider_reference else {'currency': currency},
    )
    db.add(operation)
    db.flush()  # Get operation.id
    
    # Create ledger entries (double-entry)
    # CREDIT user's WALLET_BLOCKED
    credit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=blocked_account_id,
        amount=amount,
        currency=currency,
        entry_type=LedgerEntryType.CREDIT,
    )
    
    # DEBIT INTERNAL_OMNIBUS
    debit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=omnibus_account_id,
        amount=-amount,  # Negative for DEBIT
        currency=currency,
        entry_type=LedgerEntryType.DEBIT,
    )
    
    db.add(credit_entry)
    db.add(debit_entry)
    db.flush()
    
    # Create audit log
    audit_log = AuditLog(
        actor_user_id=None,  # System operation
        actor_role=Role.OPS,
        action="DEPOSIT_RECORDED",
        entity_type="Operation",
        entity_id=operation.id,
        before=None,
        after={
            'operation_id': str(operation.id),
            'user_id': str(user_id),
            'currency': currency,
            'amount': str(amount),
            'account_type': AccountType.WALLET_BLOCKED.value,
        },
        reason=None,
    )
    db.add(audit_log)
    
    # Validate double-entry invariant before commit
    if not validate_double_entry_invariant(db, operation.id):
        db.rollback()
        raise ValidationError("Double-entry accounting invariant violation detected")
    
    # Recompute Transaction status if transaction_id provided
    if transaction_id:
        try:
            recompute_transaction_status(db=db, transaction_id=transaction_id)
        except Exception:
            # If transaction doesn't exist or error, continue
            # Status recomputation is non-critical for operation completion
            pass
    
    db.commit()
    return operation


def release_compliance_funds(
    *,
    db: Session,
    user_id: UUID,
    currency: str,
    amount: Decimal,
    transaction_id: Optional[UUID] = None,
    reason: str,
    actor_user_id: Optional[UUID] = None,
) -> Operation:
    """
    Release funds from WALLET_BLOCKED to WALLET_AVAILABLE after compliance review.
    
    Creates:
    - Operation (RELEASE_FUNDS, COMPLETED)
    - LedgerEntries: DEBIT WALLET_BLOCKED, CREDIT WALLET_AVAILABLE
    - AuditLog
    
    Raises InsufficientBalanceError if insufficient balance in WALLET_BLOCKED.
    """
    # Validate amount
    if amount <= 0:
        raise ValidationError("Amount must be greater than 0")
    
    # Ensure wallet accounts exist
    wallet_accounts = ensure_wallet_accounts(db, user_id, currency)
    blocked_account_id = wallet_accounts[AccountType.WALLET_BLOCKED.value]
    available_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
    
    # Check balance
    blocked_balance = get_account_balance(db, blocked_account_id)
    if blocked_balance < amount:
        raise InsufficientBalanceError(
            f"Insufficient balance in WALLET_BLOCKED: {blocked_balance} < {amount}"
        )
    
    # Create operation
    operation = Operation(
        transaction_id=transaction_id,
        type=OperationType.RELEASE_FUNDS,
        status=OperationStatus.COMPLETED,
        idempotency_key=None,
        metadata={
            'currency': currency,
            'reason': reason,
        },
    )
    db.add(operation)
    db.flush()
    
    # Create ledger entries (double-entry)
    # DEBIT WALLET_BLOCKED
    debit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=blocked_account_id,
        amount=-amount,  # Negative for DEBIT
        currency=currency,
        entry_type=LedgerEntryType.DEBIT,
    )
    
    # CREDIT WALLET_AVAILABLE
    credit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=available_account_id,
        amount=amount,
        currency=currency,
        entry_type=LedgerEntryType.CREDIT,
    )
    
    db.add(debit_entry)
    db.add(credit_entry)
    db.flush()
    
    # Create audit log
    audit_log = AuditLog(
        actor_user_id=actor_user_id,
        actor_role=Role.COMPLIANCE,
        action="COMPLIANCE_RELEASE",
        entity_type="Operation",
        entity_id=operation.id,
        before={
            'blocked_balance': str(blocked_balance),
            'transaction_id': str(transaction_id) if transaction_id else None,
        },
        after={
            'operation_id': str(operation.id),
            'user_id': str(user_id),
            'currency': currency,
            'amount': str(amount),
            'new_blocked_balance': str(blocked_balance - amount),
        },
        reason=reason,
    )
    db.add(audit_log)
    
    # Validate double-entry invariant before commit
    if not validate_double_entry_invariant(db, operation.id):
        db.rollback()
        raise ValidationError("Double-entry accounting invariant violation detected")
    
    # Recompute Transaction status if transaction_id provided
    if transaction_id:
        try:
            recompute_transaction_status(db=db, transaction_id=transaction_id)
        except Exception:
            # If transaction doesn't exist or error, continue
            # Status recomputation is non-critical for operation completion
            pass
    
    db.commit()
    return operation


def lock_funds_for_investment(
    *,
    db: Session,
    user_id: UUID,
    currency: str,
    amount: Decimal,
    transaction_id: Optional[UUID] = None,
    reason: Optional[str] = None,
) -> Operation:
    """
    Lock funds from WALLET_AVAILABLE to WALLET_LOCKED for investment.
    
    Creates:
    - Operation (INVEST_EXCLUSIVE, COMPLETED)
    - LedgerEntries: DEBIT WALLET_AVAILABLE, CREDIT WALLET_LOCKED
    - AuditLog
    
    Raises InsufficientBalanceError if insufficient balance in WALLET_AVAILABLE.
    """
    # Validate amount
    if amount <= 0:
        raise ValidationError("Amount must be greater than 0")
    
    # Ensure wallet accounts exist
    wallet_accounts = ensure_wallet_accounts(db, user_id, currency)
    available_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
    locked_account_id = wallet_accounts[AccountType.WALLET_LOCKED.value]
    
    # Check balance
    available_balance = get_account_balance(db, available_account_id)
    if available_balance < amount:
        raise InsufficientBalanceError(
            f"Insufficient balance in WALLET_AVAILABLE: {available_balance} < {amount}"
        )
    
    # Create operation
    operation = Operation(
        transaction_id=transaction_id,
        type=OperationType.INVEST_EXCLUSIVE,
        status=OperationStatus.COMPLETED,
        idempotency_key=None,
        metadata={
            'currency': currency,
            'reason': reason,
        } if reason else {'currency': currency},
    )
    db.add(operation)
    db.flush()
    
    # Create ledger entries (double-entry)
    # DEBIT WALLET_AVAILABLE
    debit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=available_account_id,
        amount=-amount,  # Negative for DEBIT
        currency=currency,
        entry_type=LedgerEntryType.DEBIT,
    )
    
    # CREDIT WALLET_LOCKED
    credit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=locked_account_id,
        amount=amount,
        currency=currency,
        entry_type=LedgerEntryType.CREDIT,
    )
    
    db.add(debit_entry)
    db.add(credit_entry)
    db.flush()
    
    # Create audit log
    audit_log = AuditLog(
        actor_user_id=None,  # User-initiated (future: pass user_id from authenticated user)
        actor_role=Role.USER,
        action="FUNDS_LOCKED_FOR_INVESTMENT",
        entity_type="Operation",
        entity_id=operation.id,
        before={
            'available_balance': str(available_balance),
            'transaction_id': str(transaction_id) if transaction_id else None,
        },
        after={
            'operation_id': str(operation.id),
            'user_id': str(user_id),
            'currency': currency,
            'amount': str(amount),
            'new_available_balance': str(available_balance - amount),
        },
        reason=reason,
    )
    db.add(audit_log)
    
    # Validate double-entry invariant before commit
    if not validate_double_entry_invariant(db, operation.id):
        db.rollback()
        raise ValidationError("Double-entry accounting invariant violation detected")
    
    # Recompute Transaction status if transaction_id provided
    if transaction_id:
        try:
            recompute_transaction_status(db=db, transaction_id=transaction_id)
        except Exception:
            # If transaction doesn't exist or error, continue
            # Status recomputation is non-critical for operation completion
            pass
    
    db.commit()
    return operation


def reject_deposit(
    *,
    db: Session,
    transaction_id: UUID,
    user_id: UUID,
    currency: str,
    amount: Decimal,
    reason: str,
    actor_user_id: Optional[UUID] = None,
) -> Operation:
    """
    Reject a deposit by reversing it (moving funds from BLOCKED back to INTERNAL_OMNIBUS).
    
    This is used when a deposit is rejected during compliance review.
    Creates a reversal operation that moves funds back to the internal account.
    
    Creates:
    - Operation (REVERSAL_DEPOSIT, COMPLETED)
    - LedgerEntries: DEBIT WALLET_BLOCKED, CREDIT INTERNAL_OMNIBUS
    - AuditLog (DEPOSIT_REJECTED, COMPLIANCE role, reason required)
    
    This preserves ledger immutability - no entries are deleted or modified.
    The reversal creates new immutable entries that offset the original deposit.
    """
    # Validate amount
    if amount <= 0:
        raise ValidationError("Amount must be greater than 0")
    
    if not reason:
        raise ValidationError("Reason is required for deposit rejection")
    
    # Ensure wallet accounts exist
    wallet_accounts = ensure_wallet_accounts(db, user_id, currency)
    blocked_account_id = wallet_accounts[AccountType.WALLET_BLOCKED.value]
    
    # Get or create INTERNAL_OMNIBUS account (idempotent)
    omnibus_account = db.query(Account).filter(
        Account.account_type == AccountType.INTERNAL_OMNIBUS,
        Account.currency == currency,
    ).first()
    
    if not omnibus_account:
        # Create INTERNAL_OMNIBUS account if it doesn't exist (idempotent)
        omnibus_account = Account(
            id=uuid4(),
            user_id=None,  # System account (no user)
            currency=currency,
            account_type=AccountType.INTERNAL_OMNIBUS,
        )
        db.add(omnibus_account)
        db.flush()  # Get account.id
    
    omnibus_account_id = omnibus_account.id
    
    # Check blocked balance
    blocked_balance = get_account_balance(db, blocked_account_id)
    if blocked_balance < amount:
        raise InsufficientBalanceError(
            f"Insufficient balance in WALLET_BLOCKED: {blocked_balance} < {amount}"
        )
    
    # Create reversal operation
    operation = Operation(
        transaction_id=transaction_id,
        type=OperationType.REVERSAL_DEPOSIT,
        status=OperationStatus.COMPLETED,
        idempotency_key=None,
        metadata={
            'currency': currency,
            'reason': reason,
            'reversal_type': 'deposit_rejection',
        },
    )
    db.add(operation)
    db.flush()
    
    # Create ledger entries (double-entry reversal)
    # DEBIT WALLET_BLOCKED (remove funds from user)
    debit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=blocked_account_id,
        amount=-amount,  # Negative for DEBIT
        currency=currency,
        entry_type=LedgerEntryType.DEBIT,
    )
    
    # CREDIT INTERNAL_OMNIBUS (return funds to internal account)
    credit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=omnibus_account_id,
        amount=amount,
        currency=currency,
        entry_type=LedgerEntryType.CREDIT,
    )
    
    db.add(debit_entry)
    db.add(credit_entry)
    db.flush()
    
    # Create audit log
    audit_log = AuditLog(
        actor_user_id=actor_user_id,
        actor_role=Role.COMPLIANCE,
        action="DEPOSIT_REJECTED",
        entity_type="Operation",
        entity_id=operation.id,
        before={
            'blocked_balance': str(blocked_balance),
            'transaction_id': str(transaction_id),
        },
        after={
            'operation_id': str(operation.id),
            'user_id': str(user_id),
            'currency': currency,
            'amount': str(amount),
            'new_blocked_balance': str(blocked_balance - amount),
            'reversal_type': 'deposit_rejection',
        },
        reason=reason,  # Required for compliance actions
    )
    db.add(audit_log)
    
    # Validate double-entry invariant before commit
    if not validate_double_entry_invariant(db, operation.id):
        db.rollback()
        raise ValidationError("Double-entry accounting invariant violation detected")
    
    # Recompute Transaction status if transaction_id provided
    if transaction_id:
        try:
            recompute_transaction_status(db=db, transaction_id=transaction_id)
        except Exception:
            # If transaction doesn't exist or error, continue
            # Status recomputation is non-critical for operation completion
            pass
    
    db.commit()
    return operation
