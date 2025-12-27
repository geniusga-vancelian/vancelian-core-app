"""
Tests for AVENIR vesting lots backfill script
"""

import pytest
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.core.ledger.models import Operation, OperationType, OperationStatus, LedgerEntry, LedgerEntryType
from app.core.accounts.models import Account, AccountType
from app.core.vaults.models import VestingLot, VestingLotStatus, Vault
from scripts.backfill_avenir_vesting_lots import (
    get_user_id_from_operation,
    get_deposit_amount_from_operation,
    normalize_to_utc_midnight,
    backfill_avenir_vesting_lots,
)


def test_normalize_to_utc_midnight():
    """Test date normalization"""
    dt = datetime(2025, 1, 15, 14, 32, 18, tzinfo=timezone.utc)
    result = normalize_to_utc_midnight(dt)
    assert result == date(2025, 1, 15)
    
    # Test with date object
    d = date(2025, 1, 15)
    result = normalize_to_utc_midnight(d)
    assert result == date(2025, 1, 15)


def test_backfill_idempotent(db_session, test_user, avenir_vault):
    """
    Test that backfill is idempotent: running twice produces same count
    """
    # Create a VAULT_DEPOSIT operation
    user_id = test_user.id
    currency = "AED"
    amount = Decimal("10000.00")
    
    # Ensure wallet accounts exist
    from app.services.wallet_helpers import ensure_wallet_accounts
    wallet_accounts = ensure_wallet_accounts(db_session, user_id, currency)
    user_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
    
    # Get vault pool account
    from app.services.wallet_helpers import get_or_create_system_account
    vault_pool_account = db_session.query(Account).filter(
        Account.account_type == AccountType.VAULT_POOL_CASH,
        Account.vault_id == avenir_vault.id,
        Account.currency == currency,
    ).first()
    if not vault_pool_account:
        vault_pool_account = Account(
            id=uuid4(),
            user_id=None,
            currency=currency,
            account_type=AccountType.VAULT_POOL_CASH,
            vault_id=avenir_vault.id,
        )
        db_session.add(vault_pool_account)
        db_session.flush()
    
    # Create operation
    operation = Operation(
        transaction_id=None,
        type=OperationType.VAULT_DEPOSIT,
        status=OperationStatus.COMPLETED,
        idempotency_key=None,
        operation_metadata={
            'currency': currency,
            'vault_code': 'AVENIR',
            'vault_id': str(avenir_vault.id),
        },
    )
    db_session.add(operation)
    db_session.flush()
    
    # Create ledger entries
    debit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=user_account_id,
        amount=-amount,  # Negative for DEBIT
        currency=currency,
        entry_type=LedgerEntryType.DEBIT,
    )
    credit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=vault_pool_account.id,
        amount=amount,
        currency=currency,
        entry_type=LedgerEntryType.CREDIT,
    )
    db_session.add(debit_entry)
    db_session.add(credit_entry)
    db_session.commit()
    
    # Run backfill first time
    stats1 = backfill_avenir_vesting_lots(
        db=db_session,
        currency=currency,
        user_id=user_id,
        dry_run=False,
    )
    
    assert stats1['created_count'] == 1
    assert stats1['skipped_count'] == 0
    assert len(stats1['errors']) == 0
    
    # Verify lot was created
    lot = db_session.query(VestingLot).filter(
        VestingLot.source_operation_id == operation.id
    ).first()
    assert lot is not None
    assert lot.amount == amount
    assert lot.user_id == user_id
    assert lot.vault_code == 'AVENIR'
    assert lot.status == VestingLotStatus.VESTED.value
    
    # Run backfill second time (idempotent)
    stats2 = backfill_avenir_vesting_lots(
        db=db_session,
        currency=currency,
        user_id=user_id,
        dry_run=False,
    )
    
    assert stats2['created_count'] == 0
    assert stats2['skipped_count'] == 1  # Skipped because already exists
    assert len(stats2['errors']) == 0
    
    # Verify only one lot exists
    lots = db_session.query(VestingLot).filter(
        VestingLot.source_operation_id == operation.id
    ).all()
    assert len(lots) == 1


def test_backfill_deposit_day_bucketing(db_session, test_user, avenir_vault):
    """
    Test that deposit_day is correctly normalized to UTC date
    """
    user_id = test_user.id
    currency = "AED"
    amount = Decimal("5000.00")
    
    # Ensure wallet accounts exist
    from app.services.wallet_helpers import ensure_wallet_accounts
    wallet_accounts = ensure_wallet_accounts(db_session, user_id, currency)
    user_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
    
    # Get vault pool account
    vault_pool_account = db_session.query(Account).filter(
        Account.account_type == AccountType.VAULT_POOL_CASH,
        Account.vault_id == avenir_vault.id,
        Account.currency == currency,
    ).first()
    if not vault_pool_account:
        vault_pool_account = Account(
            id=uuid4(),
            user_id=None,
            currency=currency,
            account_type=AccountType.VAULT_POOL_CASH,
            vault_id=avenir_vault.id,
        )
        db_session.add(vault_pool_account)
        db_session.flush()
    
    # Create operation with specific timestamp
    deposit_timestamp = datetime(2025, 1, 15, 14, 32, 18, tzinfo=timezone.utc)
    operation = Operation(
        transaction_id=None,
        type=OperationType.VAULT_DEPOSIT,
        status=OperationStatus.COMPLETED,
        idempotency_key=None,
        operation_metadata={
            'currency': currency,
            'vault_code': 'AVENIR',
            'vault_id': str(avenir_vault.id),
        },
        created_at=deposit_timestamp,
    )
    db_session.add(operation)
    db_session.flush()
    
    # Create ledger entries
    debit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=user_account_id,
        amount=-amount,
        currency=currency,
        entry_type=LedgerEntryType.DEBIT,
    )
    credit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=vault_pool_account.id,
        amount=amount,
        currency=currency,
        entry_type=LedgerEntryType.CREDIT,
    )
    db_session.add(debit_entry)
    db_session.add(credit_entry)
    db_session.commit()
    
    # Run backfill
    stats = backfill_avenir_vesting_lots(
        db=db_session,
        currency=currency,
        user_id=user_id,
        dry_run=False,
    )
    
    assert stats['created_count'] == 1
    
    # Verify deposit_day and release_day
    lot = db_session.query(VestingLot).filter(
        VestingLot.source_operation_id == operation.id
    ).first()
    
    assert lot.deposit_day == date(2025, 1, 15)  # Normalized to date
    assert lot.release_day == date(2025, 1, 15) + timedelta(days=365)  # deposit_day + 365
    assert lot.release_day == date(2026, 1, 15)


def test_backfill_release_day_calculation(db_session, test_user, avenir_vault):
    """
    Test that release_day = deposit_day + 365 days
    """
    user_id = test_user.id
    currency = "AED"
    amount = Decimal("3000.00")
    
    # Ensure wallet accounts exist
    from app.services.wallet_helpers import ensure_wallet_accounts
    wallet_accounts = ensure_wallet_accounts(db_session, user_id, currency)
    user_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
    
    # Get vault pool account
    vault_pool_account = db_session.query(Account).filter(
        Account.account_type == AccountType.VAULT_POOL_CASH,
        Account.vault_id == avenir_vault.id,
        Account.currency == currency,
    ).first()
    if not vault_pool_account:
        vault_pool_account = Account(
            id=uuid4(),
            user_id=None,
            currency=currency,
            account_type=AccountType.VAULT_POOL_CASH,
            vault_id=avenir_vault.id,
        )
        db_session.add(vault_pool_account)
        db_session.flush()
    
    # Create operation
    deposit_day = date(2024, 6, 1)
    deposit_timestamp = datetime.combine(deposit_day, datetime.min.time(), tzinfo=timezone.utc)
    
    operation = Operation(
        transaction_id=None,
        type=OperationType.VAULT_DEPOSIT,
        status=OperationStatus.COMPLETED,
        idempotency_key=None,
        operation_metadata={
            'currency': currency,
            'vault_code': 'AVENIR',
            'vault_id': str(avenir_vault.id),
        },
        created_at=deposit_timestamp,
    )
    db_session.add(operation)
    db_session.flush()
    
    # Create ledger entries
    debit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=user_account_id,
        amount=-amount,
        currency=currency,
        entry_type=LedgerEntryType.DEBIT,
    )
    credit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=vault_pool_account.id,
        amount=amount,
        currency=currency,
        entry_type=LedgerEntryType.CREDIT,
    )
    db_session.add(debit_entry)
    db_session.add(credit_entry)
    db_session.commit()
    
    # Run backfill
    stats = backfill_avenir_vesting_lots(
        db=db_session,
        currency=currency,
        user_id=user_id,
        dry_run=False,
    )
    
    assert stats['created_count'] == 1
    
    # Verify release_day calculation
    lot = db_session.query(VestingLot).filter(
        VestingLot.source_operation_id == operation.id
    ).first()
    
    expected_release_day = deposit_day + timedelta(days=365)
    assert lot.release_day == expected_release_day
    assert lot.release_day == date(2025, 6, 1)

