"""
Vault service - Deposit and withdrawal logic
"""

from decimal import Decimal
from datetime import datetime, timedelta, timezone
from uuid import UUID
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.vaults.models import Vault, VaultAccount, WithdrawalRequest, VaultStatus, WithdrawalRequestStatus
from app.core.ledger.models import Operation, OperationType, OperationStatus, LedgerEntry, LedgerEntryType
from app.core.accounts.models import Account
from app.core.accounts.wallet_locks import WalletLock, LockReason, ReferenceType, LockStatus
from app.services.vault_helpers import (
    get_user_wallet_available_account,
    get_or_create_vault_pool_cash_account,
    get_vault_cash_balance,
)
from app.services.wallet_helpers import get_account_balance
from app.utils.ledger_validator import validate_double_entry_invariant


class VaultError(Exception):
    """Base exception for vault operations"""
    pass


class VaultNotFoundError(VaultError):
    """Raised when vault is not found"""
    pass


class VaultPausedError(VaultError):
    """Raised when vault is paused"""
    pass


class VaultLockedError(VaultError):
    """Raised when vault withdrawals are locked (e.g., AVENIR)"""
    pass


class InsufficientVaultBalanceError(VaultError):
    """Raised when vault has insufficient cash balance"""
    pass


class InsufficientUserBalanceError(VaultError):
    """Raised when user has insufficient balance"""
    pass


def get_vault_by_code(db: Session, vault_code: str) -> Vault:
    """
    Get vault by code.
    
    Raises VaultNotFoundError if not found.
    """
    vault = db.query(Vault).filter(Vault.code == vault_code).first()
    if not vault:
        raise VaultNotFoundError(f"Vault with code '{vault_code}' not found")
    return vault


def get_or_create_vault_account(db: Session, vault_id: UUID, user_id: UUID) -> VaultAccount:
    """
    Get or create VaultAccount for user in vault.
    
    Returns existing VaultAccount or creates a new one.
    """
    vault_account = db.query(VaultAccount).filter(
        VaultAccount.vault_id == vault_id,
        VaultAccount.user_id == user_id,
    ).first()
    
    if vault_account:
        return vault_account
    
    # Create new VaultAccount
    vault_account = VaultAccount(
        vault_id=vault_id,
        user_id=user_id,
        principal=Decimal("0.00"),
        available_balance=Decimal("0.00"),
        locked_until=None,
    )
    db.add(vault_account)
    db.flush()
    
    return vault_account


def deposit_to_vault(
    db: Session,
    user_id: UUID,
    vault_code: str,
    amount: Decimal,
    currency: str = "AED",
) -> Dict[str, Any]:
    """
    Deposit funds from user wallet to vault.
    
    Creates:
    - Operation (VAULT_DEPOSIT, COMPLETED)
    - LedgerEntries: DEBIT user WALLET_AVAILABLE, CREDIT vault VAULT_POOL_CASH
    - Updates VaultAccount.principal
    - Updates vault.cash_balance and vault.total_aum (deprecated fields, kept for backward compat)
    
    For AVENIR vault: sets locked_until = max(locked_until, now+365d)
    
    NO COMMIT - caller must commit.
    
    Returns:
        Dict with operation_id, vault_account_id, vault_snapshot
    """
    # Validate amount
    if amount <= 0:
        raise ValueError("Amount must be greater than 0")
    
    # Get and lock vault row
    vault = db.execute(
        select(Vault)
        .where(Vault.code == vault_code)
        .with_for_update()
    ).scalar_one_or_none()
    
    if not vault:
        raise VaultNotFoundError(f"Vault with code '{vault_code}' not found")
    
    # Check vault status
    if vault.status == VaultStatus.PAUSED:
        raise VaultPausedError(f"Vault '{vault_code}' is paused")
    
    # Get and lock user WALLET_AVAILABLE account
    user_account_id = get_user_wallet_available_account(db, user_id, currency)
    user_account = db.execute(
        select(Account)
        .where(Account.id == user_account_id)
        .with_for_update()
    ).scalar_one()
    
    # Check user balance
    user_balance = get_account_balance(db, user_account_id)
    if user_balance < amount:
        raise InsufficientUserBalanceError(
            f"Insufficient balance in WALLET_AVAILABLE: {user_balance} < {amount}"
        )
    
    # Get and lock vault pool cash account
    vault_pool_account_id = get_or_create_vault_pool_cash_account(db, vault.id, currency)
    vault_pool_account = db.execute(
        select(Account)
        .where(Account.id == vault_pool_account_id)
        .with_for_update()
    ).scalar_one()
    
    # Create Operation
    operation = Operation(
        transaction_id=None,
        type=OperationType.VAULT_DEPOSIT,
        status=OperationStatus.COMPLETED,
        idempotency_key=None,
        operation_metadata={
            'currency': currency,
            'vault_code': vault_code,
            'vault_id': str(vault.id),
        },
    )
    db.add(operation)
    db.flush()  # CRITICAL: Flush to ensure operation.id is available before creating WalletLock
    
    # Verify operation.id is available (safety check)
    if not operation.id:
        raise ValueError("Operation ID is not available after flush - this should never happen")
    
    # Create ledger entries (double-entry)
    # DEBIT user WALLET_AVAILABLE
    debit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=user_account_id,
        amount=-amount,  # Negative for DEBIT
        currency=currency,
        entry_type=LedgerEntryType.DEBIT,
    )
    
    # CREDIT vault VAULT_POOL_CASH
    credit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=vault_pool_account_id,
        amount=amount,
        currency=currency,
        entry_type=LedgerEntryType.CREDIT,
    )
    
    db.add(debit_entry)
    db.add(credit_entry)
    db.flush()
    
    # Validate double-entry invariant
    if not validate_double_entry_invariant(db, str(operation.id)):
        db.rollback()
        raise ValueError("Double-entry accounting invariant violation detected")
    
    # Get or create VaultAccount
    vault_account = get_or_create_vault_account(db, vault.id, user_id)
    vault_account.principal += amount
    vault_account.available_balance += amount
    
    # For AVENIR vault: set locked_until = max(locked_until, now+365d) and create wallet_lock
    if vault_code.upper() == "AVENIR":
        now = datetime.now(timezone.utc)
        locked_until_date = now + timedelta(days=365)
        if vault_account.locked_until is None or locked_until_date > vault_account.locked_until:
            vault_account.locked_until = locked_until_date
        if vault.locked_until is None or locked_until_date > vault.locked_until:
            vault.locked_until = locked_until_date
        
        # Create wallet_lock for AVENIR vesting (liability tracking)
        # This is the source of truth for Wallet Matrix VAULT_USER rows (AVENIR → locked column)
        # Idempotency: use operation_id as fallback (intent_id is for offers, not vaults)
        # For vaults, we use operation_id for idempotency (one lock per deposit operation)
        # Ensure operation.id is available (should be after db.flush() above)
        if not operation.id:
            raise ValueError("Operation ID is not available - operation must be flushed before creating wallet_lock")
        
        existing_lock = db.query(WalletLock).filter(
            WalletLock.operation_id == operation.id
        ).first()
        
        if not existing_lock:
            try:
                wallet_lock = WalletLock(
                    user_id=user_id,
                    currency=currency,
                    amount=amount,
                    reason=LockReason.VAULT_AVENIR_VESTING.value,  # AVENIR uses VAULT_AVENIR_VESTING
                    reference_type=ReferenceType.VAULT.value,
                    reference_id=vault.id,
                    status=LockStatus.ACTIVE.value,  # Always ACTIVE on creation
                    intent_id=None,  # Not applicable for vaults
                    operation_id=operation.id,  # For idempotency
                )
                db.add(wallet_lock)
                db.flush()  # Flush to catch any constraint violations early
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.exception(
                    f"Failed to create wallet_lock for AVENIR deposit: {type(e).__name__}: {str(e)}",
                    extra={"user_id": str(user_id), "vault_id": str(vault.id), "operation_id": str(operation.id)}
                )
                # Convert to ValueError so it's caught by endpoint handler and converted to HTTPException 400
                raise ValueError(f"Failed to create wallet_lock: {str(e)}") from e
    
    # Update vault deprecated fields (backward compat)
    vault.cash_balance += amount
    vault.total_aum += amount
    
    db.flush()
    
    # Build response
    vault_cash_balance = get_vault_cash_balance(db, vault.id, currency)
    
    return {
        "operation_id": str(operation.id),
        "vault_account_id": str(vault_account.id),
        "vault_snapshot": {
            "code": vault.code,
            "name": vault.name,
            "status": vault.status.value,
            "cash_balance": str(vault_cash_balance),
            "total_aum": str(vault.total_aum),
        },
    }


def request_withdrawal(
    db: Session,
    user_id: UUID,
    vault_code: str,
    amount: Decimal,
    currency: str = "AED",
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Request withdrawal from vault.
    
    If vault has sufficient cash, executes immediately:
    - Operation (VAULT_WITHDRAW_EXECUTED, COMPLETED)
    - LedgerEntries: DEBIT vault VAULT_POOL_CASH, CREDIT user WALLET_AVAILABLE
    - Updates VaultAccount.principal
    - Updates vault.cash_balance and vault.total_aum
    - Creates WithdrawalRequest(status=EXECUTED)
    
    Otherwise, creates WithdrawalRequest(status=PENDING) for FIFO processing.
    
    NO COMMIT - caller must commit.
    
    Returns:
        Dict with request_id, status, operation_id (if EXECUTED), vault_snapshot
    """
    # Validate amount
    if amount <= 0:
        raise ValueError("Amount must be greater than 0")
    
    # Get and lock vault row
    vault = db.execute(
        select(Vault)
        .where(Vault.code == vault_code)
        .with_for_update()
    ).scalar_one_or_none()
    
    if not vault:
        raise VaultNotFoundError(f"Vault with code '{vault_code}' not found")
    
    # Check vault status
    if vault.status == VaultStatus.PAUSED:
        raise VaultPausedError(f"Vault '{vault_code}' is paused")
    
    # Get VaultAccount
    vault_account = get_or_create_vault_account(db, vault.id, user_id)
    
    # Check AVENIR lock: if locked_until > now -> 403 LOCKED
    if vault_account.locked_until:
        now = datetime.now(timezone.utc)
        if vault_account.locked_until > now:
            raise VaultLockedError(
                f"Vault account is locked until {vault_account.locked_until.isoformat()}"
            )
    
    # Check vault-level lock (for AVENIR)
    if vault.locked_until:
        now = datetime.now(timezone.utc)
        if vault.locked_until > now:
            raise VaultLockedError(
                f"Vault is locked until {vault.locked_until.isoformat()}"
            )
    
    # Lock VaultAccount
    vault_account = db.execute(
        select(VaultAccount)
        .where(VaultAccount.id == vault_account.id)
        .with_for_update()
    ).scalar_one()
    
    # Ensure VaultAccount principal >= amount
    if vault_account.principal < amount:
        raise InsufficientUserBalanceError(
            f"Insufficient principal in vault account: {vault_account.principal} < {amount}"
        )
    
    # Get and lock accounts first
    user_account_id = get_user_wallet_available_account(db, user_id, currency)
    user_account = db.execute(
        select(Account)
        .where(Account.id == user_account_id)
        .with_for_update()
    ).scalar_one()
    
    vault_pool_account_id = get_or_create_vault_pool_cash_account(db, vault.id, currency)
    vault_pool_account = db.execute(
        select(Account)
        .where(Account.id == vault_pool_account_id)
        .with_for_update()
    ).scalar_one()
    
    # Get vault cash balance (from ledger, source of truth) - after locking accounts
    vault_cash_balance = get_vault_cash_balance(db, vault.id, currency)
    
    # Check if vault has sufficient cash
    if vault_cash_balance >= amount:
        # Execute immediately (accounts already locked above)
        # Create Operation
        operation = Operation(
            transaction_id=None,
            type=OperationType.VAULT_WITHDRAW_EXECUTED,
            status=OperationStatus.COMPLETED,
            idempotency_key=None,
            operation_metadata={
                'currency': currency,
                'vault_code': vault_code,
                'vault_id': str(vault.id),
            },
        )
        db.add(operation)
        db.flush()
        
        # Create ledger entries (double-entry, reversed from deposit)
        # DEBIT vault VAULT_POOL_CASH
        debit_entry = LedgerEntry(
            operation_id=operation.id,
            account_id=vault_pool_account_id,
            amount=-amount,  # Negative for DEBIT
            currency=currency,
            entry_type=LedgerEntryType.DEBIT,
        )
        
        # CREDIT user WALLET_AVAILABLE
        credit_entry = LedgerEntry(
            operation_id=operation.id,
            account_id=user_account_id,
            amount=amount,
            currency=currency,
            entry_type=LedgerEntryType.CREDIT,
        )
        
        db.add(debit_entry)
        db.add(credit_entry)
        db.flush()
        
        # Validate double-entry invariant
        if not validate_double_entry_invariant(db, str(operation.id)):
            db.rollback()
            raise ValueError("Double-entry accounting invariant violation detected")
        
        # Update VaultAccount
        vault_account.principal -= amount
        vault_account.available_balance -= amount
        
        # For AVENIR: release wallet_locks proportionally (oldest ACTIVE rows first)
        if vault_code.upper() == "AVENIR":
            # Get active wallet_locks for this vault + user, ordered by created_at (oldest first)
            active_locks = db.execute(
                select(WalletLock)
                .where(
                    WalletLock.user_id == user_id,
                    WalletLock.reference_type == "VAULT",
                    WalletLock.reference_id == vault.id,
                    WalletLock.reason == LockReason.VAULT_AVENIR_VESTING.value,
                    WalletLock.status == LockStatus.ACTIVE.value,
                )
                .order_by(WalletLock.created_at)
                .with_for_update()
            ).scalars().all()
            
            remaining_to_release = amount
            
            for lock in active_locks:
                if remaining_to_release <= 0:
                    break
                
                if lock.amount <= remaining_to_release:
                    # Release entire lock
                    lock.status = LockStatus.RELEASED.value
                    lock.released_at = datetime.now(timezone.utc)
                    remaining_to_release -= lock.amount
                else:
                    # Partial release: create new row for remaining amount, mark current as released
                    remaining_amount = lock.amount - remaining_to_release
                    lock.status = LockStatus.RELEASED.value
                    lock.released_at = datetime.now(timezone.utc)
                    
                    # Create new lock for remaining amount
                    new_lock = WalletLock(
                        user_id=user_id,
                        currency=lock.currency,
                        amount=remaining_amount,
                        reason=LockReason.VAULT_AVENIR_VESTING.value,
                        reference_type=lock.reference_type,
                        reference_id=lock.reference_id,
                        status=LockStatus.ACTIVE.value,
                        intent_id=None,
                        operation_id=None,  # Original operation_id not applicable for partial release
                    )
                    db.add(new_lock)
                    remaining_to_release = Decimal("0.00")
        
        # Update vault deprecated fields
        vault.cash_balance -= amount
        vault.total_aum -= amount
        
        # Create WithdrawalRequest with EXECUTED status
        withdrawal_request = WithdrawalRequest(
            vault_id=vault.id,
            user_id=user_id,
            amount=amount,
            status=WithdrawalRequestStatus.EXECUTED,
            reason=reason,
            executed_at=datetime.now(timezone.utc),
        )
        db.add(withdrawal_request)
        db.flush()
        
        # Get updated vault cash balance
        updated_vault_cash_balance = get_vault_cash_balance(db, vault.id, currency)
        
        return {
            "request_id": str(withdrawal_request.id),
            "status": "EXECUTED",
            "operation_id": str(operation.id),
            "vault_snapshot": {
                "code": vault.code,
                "name": vault.name,
                "status": vault.status.value,
                "cash_balance": str(updated_vault_cash_balance),
                "total_aum": str(vault.total_aum),
            },
        }
    else:
        # Insufficient cash - create PENDING request
        withdrawal_request = WithdrawalRequest(
            vault_id=vault.id,
            user_id=user_id,
            amount=amount,
            status=WithdrawalRequestStatus.PENDING,
            reason=reason,
            executed_at=None,
        )
        db.add(withdrawal_request)
        db.flush()
        
        vault_cash_balance = get_vault_cash_balance(db, vault.id, currency)
        
        return {
            "request_id": str(withdrawal_request.id),
            "status": "PENDING",
            "operation_id": None,
            "vault_snapshot": {
                "code": vault.code,
                "name": vault.name,
                "status": vault.status.value,
                "cash_balance": str(vault_cash_balance),
                "total_aum": str(vault.total_aum),
            },
        }


def process_pending_withdrawals(
    db: Session,
    vault_code: str,
) -> Dict[str, int]:
    """
    Process pending withdrawal requests in FIFO order.
    
    Locks vault and processes requests one by one until vault cash is insufficient.
    
    NO COMMIT - caller must commit.
    
    Returns:
        Dict with processed_count, remaining_count
    """
    # Get and lock vault row
    vault = db.execute(
        select(Vault)
        .where(Vault.code == vault_code)
        .with_for_update()
    ).scalar_one_or_none()
    
    if not vault:
        raise VaultNotFoundError(f"Vault with code '{vault_code}' not found")
    
    # Get pending requests ordered by created_at (FIFO) with SKIP LOCKED
    pending_requests = db.execute(
        select(WithdrawalRequest)
        .where(
            WithdrawalRequest.vault_id == vault.id,
            WithdrawalRequest.status == WithdrawalRequestStatus.PENDING,
        )
        .order_by(WithdrawalRequest.created_at)
        .with_for_update(skip_locked=True)
    ).scalars().all()
    
    processed_count = 0
    
    for request in pending_requests:
        # Lock VaultAccount
        vault_account = db.execute(
            select(VaultAccount)
            .where(
                VaultAccount.vault_id == vault.id,
                VaultAccount.user_id == request.user_id,
            )
            .with_for_update()
        ).scalar_one_or_none()
        
        if not vault_account:
            # VaultAccount doesn't exist - reject request
            request.status = WithdrawalRequestStatus.CANCELLED
            request.reason = "Vault account not found"
            continue
        
        # Check principal
        if vault_account.principal < request.amount:
            # Insufficient principal - reject
            request.status = WithdrawalRequestStatus.CANCELLED
            request.reason = f"Insufficient principal: {vault_account.principal} < {request.amount}"
            continue
        
        # Get vault cash balance (from ledger, source of truth)
        vault_cash_balance = get_vault_cash_balance(db, vault.id, "AED")  # TODO: support multi-currency
        
        # Check if vault has sufficient cash
        if vault_cash_balance < request.amount:
            # Break - no more withdrawals can be processed
            break
        
        # Execute withdrawal
        # Get and lock accounts
        user_account_id = get_user_wallet_available_account(db, request.user_id, "AED")
        user_account = db.execute(
            select(Account)
            .where(Account.id == user_account_id)
            .with_for_update()
        ).scalar_one()
        
        vault_pool_account_id = get_or_create_vault_pool_cash_account(db, vault.id, "AED")
        vault_pool_account = db.execute(
            select(Account)
            .where(Account.id == vault_pool_account_id)
            .with_for_update()
        ).scalar_one()
        
        # Create Operation
        operation = Operation(
            transaction_id=None,
            type=OperationType.VAULT_WITHDRAW_EXECUTED,
            status=OperationStatus.COMPLETED,
            idempotency_key=None,
            operation_metadata={
                'currency': "AED",
                'vault_code': vault_code,
                'vault_id': str(vault.id),
                'withdrawal_request_id': str(request.id),
            },
        )
        db.add(operation)
        db.flush()
        
        # Create ledger entries
        debit_entry = LedgerEntry(
            operation_id=operation.id,
            account_id=vault_pool_account_id,
            amount=-request.amount,
            currency="AED",
            entry_type=LedgerEntryType.DEBIT,
        )
        
        credit_entry = LedgerEntry(
            operation_id=operation.id,
            account_id=user_account_id,
            amount=request.amount,
            currency="AED",
            entry_type=LedgerEntryType.CREDIT,
        )
        
        db.add(debit_entry)
        db.add(credit_entry)
        db.flush()
        
        # Validate double-entry invariant
        if not validate_double_entry_invariant(db, str(operation.id)):
            db.rollback()
            raise ValueError("Double-entry accounting invariant violation detected")
        
        # Update VaultAccount
        vault_account.principal -= request.amount
        vault_account.available_balance -= request.amount
        
        # For AVENIR: release wallet_locks proportionally (oldest ACTIVE rows first)
        if vault.code.upper() == "AVENIR":
            # Get active wallet_locks for this vault + user, ordered by created_at (oldest first)
            active_locks = db.execute(
                select(WalletLock)
                .where(
                    WalletLock.user_id == request.user_id,
                    WalletLock.reference_type == "VAULT",
                    WalletLock.reference_id == vault.id,
                    WalletLock.reason == LockReason.VAULT_AVENIR_VESTING.value,
                    WalletLock.status == LockStatus.ACTIVE.value,
                )
                .order_by(WalletLock.created_at)
                .with_for_update()
            ).scalars().all()
            
            remaining_to_release = request.amount
            
            for lock in active_locks:
                if remaining_to_release <= 0:
                    break
                
                if lock.amount <= remaining_to_release:
                    # Release entire lock
                    lock.status = LockStatus.RELEASED.value
                    lock.released_at = datetime.now(timezone.utc)
                    remaining_to_release -= lock.amount
                else:
                    # Partial release: create new row for remaining amount, mark current as released
                    remaining_amount = lock.amount - remaining_to_release
                    lock.status = LockStatus.RELEASED.value
                    lock.released_at = datetime.now(timezone.utc)
                    
                    # Create new lock for remaining amount
                    new_lock = WalletLock(
                        user_id=request.user_id,
                        currency=lock.currency,
                        amount=remaining_amount,
                        reason=LockReason.VAULT_AVENIR_VESTING.value,
                        reference_type=lock.reference_type,
                        reference_id=lock.reference_id,
                        status=LockStatus.ACTIVE.value,
                        intent_id=None,
                        operation_id=None,
                    )
                    db.add(new_lock)
                    remaining_to_release = Decimal("0.00")
        
        # Update vault deprecated fields
        vault.cash_balance -= request.amount
        vault.total_aum -= request.amount
        
        # Mark request as EXECUTED
        request.status = WithdrawalRequestStatus.EXECUTED
        request.executed_at = datetime.now(timezone.utc)
        
        processed_count += 1
    
    db.flush()
    
    # Count remaining pending requests
    remaining_count = db.query(WithdrawalRequest).filter(
        WithdrawalRequest.vault_id == vault.id,
        WithdrawalRequest.status == WithdrawalRequestStatus.PENDING,
    ).count()
    
    return {
        "processed_count": processed_count,
        "remaining_count": remaining_count,
    }
