"""
Tests for AVENIR vesting release job
"""

import pytest
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.core.ledger.models import Operation, OperationType, OperationStatus, LedgerEntry, LedgerEntryType
from app.core.accounts.models import Account, AccountType
from app.core.vaults.models import VestingLot, VestingLotStatus, Vault
from app.core.accounts.wallet_locks import WalletLock, LockReason, LockStatus
from app.services.vesting_service import release_avenir_vesting_lots
from app.services.wallet_helpers import ensure_wallet_accounts, get_wallet_balances


def test_release_job_releases_mature_lot(db_session, test_user, avenir_vault):
    """
    Test that release job releases a mature lot:
    - Creates lot with release_day <= today, released_amount=0
    - Creates WALLET_LOCKED balance sufficient
    - Runs release -> lot RELEASED, ledger entries created
    - WALLET_AVAILABLE increases, WALLET_LOCKED decreases
    """
    user_id = test_user.id
    currency = "AED"
    amount = Decimal("10000.00")
    
    # Ensure wallet accounts exist
    wallet_accounts = ensure_wallet_accounts(db_session, user_id, currency)
    locked_account_id = wallet_accounts[AccountType.WALLET_LOCKED.value]
    available_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
    
    # Create initial locked balance (simulate deposit)
    operation_deposit = Operation(
        transaction_id=None,
        type=OperationType.VAULT_DEPOSIT,
        status=OperationStatus.COMPLETED,
        idempotency_key=None,
        operation_metadata={'vault_code': 'AVENIR', 'currency': currency},
    )
    db_session.add(operation_deposit)
    db_session.flush()
    
    # Create ledger entries for locked balance
    credit_locked = LedgerEntry(
        operation_id=operation_deposit.id,
        account_id=locked_account_id,
        amount=amount,  # CREDIT increases locked
        currency=currency,
        entry_type=LedgerEntryType.CREDIT,
    )
    debit_available = LedgerEntry(
        operation_id=operation_deposit.id,
        account_id=available_account_id,
        amount=-amount,  # DEBIT decreases available
        currency=currency,
        entry_type=LedgerEntryType.DEBIT,
    )
    db_session.add(credit_locked)
    db_session.add(debit_available)
    db_session.commit()
    
    # Create mature vesting lot
    deposit_day = date.today() - timedelta(days=366)  # More than 365 days ago
    release_day = deposit_day + timedelta(days=365)  # Already mature
    
    vesting_lot = VestingLot(
        vault_id=avenir_vault.id,
        vault_code='AVENIR',
        user_id=user_id,
        currency=currency,
        deposit_day=deposit_day,
        release_day=release_day,
        amount=amount,
        released_amount=Decimal('0.00'),
        status=VestingLotStatus.VESTED.value,
        source_operation_id=operation_deposit.id,
    )
    db_session.add(vesting_lot)
    db_session.commit()
    
    # Get balances before release
    balances_before = get_wallet_balances(db_session, user_id, currency)
    available_before = balances_before['available_balance']
    locked_before = balances_before['locked_balance']
    
    # Run release
    summary = release_avenir_vesting_lots(
        db=db_session,
        as_of_date=date.today(),
        currency=currency,
        dry_run=False,
    )
    
    # Verify summary
    assert summary['executed_count'] == 1
    assert summary['executed_amount'] == str(amount)
    assert summary['errors_count'] == 0
    
    # Refresh lot
    db_session.refresh(vesting_lot)
    assert vesting_lot.status == VestingLotStatus.RELEASED.value
    assert vesting_lot.released_amount == amount
    
    # Verify ledger entries created
    release_operation = db_session.query(Operation).filter(
        Operation.type == OperationType.VAULT_VESTING_RELEASE,
    ).first()
    assert release_operation is not None
    assert release_operation.status == OperationStatus.COMPLETED
    
    # Verify ledger entries
    ledger_entries = db_session.query(LedgerEntry).filter(
        LedgerEntry.operation_id == release_operation.id
    ).all()
    assert len(ledger_entries) == 2
    
    # Verify balances changed
    balances_after = get_wallet_balances(db_session, user_id, currency)
    available_after = balances_after['available_balance']
    locked_after = balances_after['locked_balance']
    
    assert available_after == available_before + amount
    assert locked_after == locked_before - amount


def test_release_job_idempotent(db_session, test_user, avenir_vault):
    """
    Test that release job is idempotent: running twice produces same result
    """
    user_id = test_user.id
    currency = "AED"
    amount = Decimal("5000.00")
    
    # Ensure wallet accounts exist
    wallet_accounts = ensure_wallet_accounts(db_session, user_id, currency)
    locked_account_id = wallet_accounts[AccountType.WALLET_LOCKED.value]
    available_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
    
    # Create initial locked balance
    operation_deposit = Operation(
        transaction_id=None,
        type=OperationType.VAULT_DEPOSIT,
        status=OperationStatus.COMPLETED,
        idempotency_key=None,
        operation_metadata={'vault_code': 'AVENIR', 'currency': currency},
    )
    db_session.add(operation_deposit)
    db_session.flush()
    
    credit_locked = LedgerEntry(
        operation_id=operation_deposit.id,
        account_id=locked_account_id,
        amount=amount,
        currency=currency,
        entry_type=LedgerEntryType.CREDIT,
    )
    debit_available = LedgerEntry(
        operation_id=operation_deposit.id,
        account_id=available_account_id,
        amount=-amount,
        currency=currency,
        entry_type=LedgerEntryType.DEBIT,
    )
    db_session.add(credit_locked)
    db_session.add(debit_available)
    db_session.commit()
    
    # Create mature vesting lot
    deposit_day = date.today() - timedelta(days=366)
    release_day = deposit_day + timedelta(days=365)
    
    vesting_lot = VestingLot(
        vault_id=avenir_vault.id,
        vault_code='AVENIR',
        user_id=user_id,
        currency=currency,
        deposit_day=deposit_day,
        release_day=release_day,
        amount=amount,
        released_amount=Decimal('0.00'),
        status=VestingLotStatus.VESTED.value,
        source_operation_id=operation_deposit.id,
    )
    db_session.add(vesting_lot)
    db_session.commit()
    
    # Run release first time
    summary1 = release_avenir_vesting_lots(
        db=db_session,
        as_of_date=date.today(),
        currency=currency,
        dry_run=False,
    )
    
    assert summary1['executed_count'] == 1
    assert summary1['executed_amount'] == str(amount)
    
    # Run release second time (idempotent)
    summary2 = release_avenir_vesting_lots(
        db=db_session,
        as_of_date=date.today(),
        currency=currency,
        dry_run=False,
    )
    
    assert summary2['executed_count'] == 0
    assert summary2['skipped_count'] >= 1  # Lot already released
    
    # Verify only one release operation exists
    release_operations = db_session.query(Operation).filter(
        Operation.type == OperationType.VAULT_VESTING_RELEASE,
    ).all()
    assert len(release_operations) == 1


def test_timeline_aggregates_same_release_day(db_session, test_user, avenir_vault):
    """
    Test that timeline aggregates multiple lots with same release_day correctly
    """
    user_id = test_user.id
    currency = "AED"
    amount1 = Decimal("5000.00")
    amount2 = Decimal("3000.00")
    release_day = date.today() + timedelta(days=100)  # Future date
    
    # Create two lots with same release_day
    deposit_day1 = release_day - timedelta(days=365)
    deposit_day2 = release_day - timedelta(days=365)
    
    # Create operations for lots
    op1 = Operation(
        transaction_id=None,
        type=OperationType.VAULT_DEPOSIT,
        status=OperationStatus.COMPLETED,
        idempotency_key=None,
        operation_metadata={'vault_code': 'AVENIR', 'currency': currency},
    )
    op2 = Operation(
        transaction_id=None,
        type=OperationType.VAULT_DEPOSIT,
        status=OperationStatus.COMPLETED,
        idempotency_key=None,
        operation_metadata={'vault_code': 'AVENIR', 'currency': currency},
    )
    db_session.add(op1)
    db_session.add(op2)
    db_session.flush()
    
    lot1 = VestingLot(
        vault_id=avenir_vault.id,
        vault_code='AVENIR',
        user_id=user_id,
        currency=currency,
        deposit_day=deposit_day1,
        release_day=release_day,
        amount=amount1,
        released_amount=Decimal('0.00'),
        status=VestingLotStatus.VESTED.value,
        source_operation_id=op1.id,
    )
    lot2 = VestingLot(
        vault_id=avenir_vault.id,
        vault_code='AVENIR',
        user_id=user_id,
        currency=currency,
        deposit_day=deposit_day2,
        release_day=release_day,
        amount=amount2,
        released_amount=Decimal('0.00'),
        status=VestingLotStatus.VESTED.value,
        source_operation_id=op2.id,
    )
    db_session.add(lot1)
    db_session.add(lot2)
    db_session.commit()
    
    # Query timeline (simulate endpoint logic)
    from sqlalchemy import func
    timeline_items = db_session.query(
        VestingLot.release_day,
        func.sum(VestingLot.amount - VestingLot.released_amount).label('total_amount')
    ).filter(
        VestingLot.vault_code == 'AVENIR',
        VestingLot.user_id == user_id,
        VestingLot.status == VestingLotStatus.VESTED.value,
        VestingLot.currency == currency,
    ).group_by(
        VestingLot.release_day
    ).order_by(
        VestingLot.release_day.asc()
    ).all()
    
    # Verify aggregation
    assert len(timeline_items) == 1
    assert timeline_items[0].release_day == release_day
    assert timeline_items[0].total_amount == amount1 + amount2

