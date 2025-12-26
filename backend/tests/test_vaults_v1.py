"""
Tests for Vaults V1 - Deposit, Withdraw, Wallet Matrix integration
"""
import pytest
from fastapi.testclient import TestClient
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.vaults.models import Vault, VaultAccount, VaultStatus, WithdrawalRequest, WithdrawalRequestStatus
from app.core.accounts.wallet_locks import WalletLock, LockReason, ReferenceType, LockStatus
from app.core.users.models import User, UserStatus
from app.core.accounts.models import Account, AccountType
from app.core.ledger.models import Operation, OperationType, OperationStatus, LedgerEntry, LedgerEntryType
from app.services.wallet_helpers import ensure_wallet_accounts, get_account_balance


def test_flex_deposit_decreases_user_available_increases_vault_pool(client: TestClient, test_user: User, db_session):
    """
    Test FLEX deposit: decreases user available, increases vault pool cash, increases vault principal
    """
    # Mock dev mode for wallet-matrix if needed
    import app.api.v1.dev as dev_module
    original_check = dev_module.check_dev_mode
    dev_module.check_dev_mode = lambda: None
    
    # Create token
    from app.api.v1.auth import create_access_token
    token = create_access_token(test_user.id, test_user.email)
    
    # Ensure wallet accounts exist
    wallet_accounts = ensure_wallet_accounts(db_session, test_user.id, "AED")
    available_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
    
    # Create initial balance (via ledger)
    operation = Operation(
        type=OperationType.DEPOSIT_AED,
        status=OperationStatus.COMPLETED,
        metadata={"test": "initial_balance"},
    )
    db_session.add(operation)
    db_session.flush()
    
    initial_amount = Decimal("10000.00")
    credit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=available_account_id,
        amount=initial_amount,
        currency="AED",
        entry_type=LedgerEntryType.CREDIT,
    )
    db_session.add(credit_entry)
    db_session.commit()
    
    # Create FLEX vault
    flex_vault = Vault(
        code="FLEX",
        name="Flexible Vault",
        status=VaultStatus.ACTIVE,
    )
    db_session.add(flex_vault)
    db_session.commit()
    
    # Deposit to FLEX
    deposit_amount = Decimal("5000.00")
    response = client.post(
        f"/api/v1/vaults/FLEX/deposits",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "amount": str(deposit_amount),
            "currency": "AED",
        },
    )
    
    # Restore original check
    dev_module.check_dev_mode = original_check
    
    assert response.status_code == 201
    data = response.json()
    assert "operation_id" in data
    assert "vault_account_id" in data
    
    # Verify user available balance decreased
    user_available_balance = get_account_balance(db_session, available_account_id)
    assert user_available_balance == initial_amount - deposit_amount, \
        f"Expected {initial_amount - deposit_amount}, got {user_available_balance}"
    
    # Verify vault_account principal increased
    vault_account = db_session.query(VaultAccount).filter(
        VaultAccount.vault_id == flex_vault.id,
        VaultAccount.user_id == test_user.id,
    ).first()
    assert vault_account is not None
    assert vault_account.principal == deposit_amount
    
    # Verify no wallet_locks created for FLEX
    wallet_locks = db_session.query(WalletLock).filter(
        WalletLock.user_id == test_user.id,
        WalletLock.reference_id == flex_vault.id,
    ).all()
    assert len(wallet_locks) == 0, "FLEX should not create wallet_locks"


def test_avenir_deposit_creates_wallet_lock_and_sets_locked_until(client: TestClient, test_user: User, db_session):
    """
    Test AVENIR deposit: same as FLEX + wallet_locks created + locked_until set
    """
    # Mock dev mode
    import app.api.v1.dev as dev_module
    original_check = dev_module.check_dev_mode
    dev_module.check_dev_mode = lambda: None
    
    # Create token
    from app.api.v1.auth import create_access_token
    token = create_access_token(test_user.id, test_user.email)
    
    # Ensure wallet accounts exist
    wallet_accounts = ensure_wallet_accounts(db_session, test_user.id, "AED")
    available_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
    
    # Create initial balance
    operation = Operation(
        type=OperationType.DEPOSIT_AED,
        status=OperationStatus.COMPLETED,
        metadata={"test": "initial_balance"},
    )
    db_session.add(operation)
    db_session.flush()
    
    initial_amount = Decimal("10000.00")
    credit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=available_account_id,
        amount=initial_amount,
        currency="AED",
        entry_type=LedgerEntryType.CREDIT,
    )
    db_session.add(credit_entry)
    db_session.commit()
    
    # Create AVENIR vault
    avenir_vault = Vault(
        code="AVENIR",
        name="Avenir Vault",
        status=VaultStatus.ACTIVE,
    )
    db_session.add(avenir_vault)
    db_session.commit()
    
    # Deposit to AVENIR
    deposit_amount = Decimal("5000.00")
    response = client.post(
        f"/api/v1/vaults/AVENIR/deposits",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "amount": str(deposit_amount),
            "currency": "AED",
        },
    )
    
    # Restore original check
    dev_module.check_dev_mode = original_check
    
    assert response.status_code == 201
    
    # Verify vault_account principal increased
    vault_account = db_session.query(VaultAccount).filter(
        VaultAccount.vault_id == avenir_vault.id,
        VaultAccount.user_id == test_user.id,
    ).first()
    assert vault_account is not None
    assert vault_account.principal == deposit_amount
    
    # Verify locked_until is set (approximately 365 days from now)
    assert vault_account.locked_until is not None
    now = datetime.now(timezone.utc)
    expected_locked_until = now + timedelta(days=365)
    # Allow 1 minute tolerance
    assert abs((vault_account.locked_until - expected_locked_until).total_seconds()) < 60
    
    # Verify wallet_lock was created
    wallet_lock = db_session.query(WalletLock).filter(
        WalletLock.user_id == test_user.id,
        WalletLock.reference_id == avenir_vault.id,
        WalletLock.reason == LockReason.VAULT_AVENIR_VESTING.value,
        WalletLock.status == LockStatus.ACTIVE.value,
    ).first()
    
    assert wallet_lock is not None, "AVENIR deposit should create wallet_lock"
    assert wallet_lock.amount == deposit_amount
    assert wallet_lock.reference_type == ReferenceType.VAULT.value


def test_avenir_withdraw_before_maturity_returns_403(client: TestClient, test_user: User, db_session):
    """
    Test AVENIR withdraw before maturity returns 403 LOCKED
    """
    # Create token
    from app.api.v1.auth import create_access_token
    token = create_access_token(test_user.id, test_user.email)
    
    # Ensure wallet accounts exist
    wallet_accounts = ensure_wallet_accounts(db_session, test_user.id, "AED")
    available_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
    
    # Create initial balance
    operation = Operation(
        type=OperationType.DEPOSIT_AED,
        status=OperationStatus.COMPLETED,
        metadata={"test": "initial_balance"},
    )
    db_session.add(operation)
    db_session.flush()
    
    initial_amount = Decimal("10000.00")
    credit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=available_account_id,
        amount=initial_amount,
        currency="AED",
        entry_type=LedgerEntryType.CREDIT,
    )
    db_session.add(credit_entry)
    db_session.commit()
    
    # Create AVENIR vault
    avenir_vault = Vault(
        code="AVENIR",
        name="Avenir Vault",
        status=VaultStatus.ACTIVE,
    )
    db_session.add(avenir_vault)
    db_session.commit()
    
    # Deposit to AVENIR
    deposit_amount = Decimal("5000.00")
    deposit_response = client.post(
        f"/api/v1/vaults/AVENIR/deposits",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "amount": str(deposit_amount),
            "currency": "AED",
        },
    )
    assert deposit_response.status_code == 201
    
    # Try to withdraw before maturity
    withdraw_amount = Decimal("2000.00")
    withdraw_response = client.post(
        f"/api/v1/vaults/AVENIR/withdrawals",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "amount": str(withdraw_amount),
            "currency": "AED",
        },
    )
    
    assert withdraw_response.status_code == 403
    error_data = withdraw_response.json()
    assert error_data["error"]["code"] == "VAULT_LOCKED"


def test_flex_withdraw_when_pool_sufficient_executes(client: TestClient, test_user: User, db_session):
    """
    Test FLEX withdraw when pool cash sufficient executes immediately
    """
    # Mock dev mode
    import app.api.v1.dev as dev_module
    original_check = dev_module.check_dev_mode
    dev_module.check_dev_mode = lambda: None
    
    # Create token
    from app.api.v1.auth import create_access_token
    token = create_access_token(test_user.id, test_user.email)
    
    # Ensure wallet accounts exist
    wallet_accounts = ensure_wallet_accounts(db_session, test_user.id, "AED")
    available_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
    
    # Create initial balance
    operation = Operation(
        type=OperationType.DEPOSIT_AED,
        status=OperationStatus.COMPLETED,
        metadata={"test": "initial_balance"},
    )
    db_session.add(operation)
    db_session.flush()
    
    initial_amount = Decimal("10000.00")
    credit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=available_account_id,
        amount=initial_amount,
        currency="AED",
        entry_type=LedgerEntryType.CREDIT,
    )
    db_session.add(credit_entry)
    db_session.commit()
    
    # Create FLEX vault
    flex_vault = Vault(
        code="FLEX",
        name="Flexible Vault",
        status=VaultStatus.ACTIVE,
    )
    db_session.add(flex_vault)
    db_session.commit()
    
    # Deposit to FLEX
    deposit_amount = Decimal("5000.00")
    deposit_response = client.post(
        f"/api/v1/vaults/FLEX/deposits",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "amount": str(deposit_amount),
            "currency": "AED",
        },
    )
    assert deposit_response.status_code == 201
    
    # Withdraw from FLEX
    withdraw_amount = Decimal("2000.00")
    withdraw_response = client.post(
        f"/api/v1/vaults/FLEX/withdrawals",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "amount": str(withdraw_amount),
            "currency": "AED",
        },
    )
    
    # Restore original check
    dev_module.check_dev_mode = original_check
    
    assert withdraw_response.status_code == 201
    data = withdraw_response.json()
    assert data["status"] == "EXECUTED"
    assert "operation_id" in data
    
    # Verify vault_account principal decreased
    vault_account = db_session.query(VaultAccount).filter(
        VaultAccount.vault_id == flex_vault.id,
        VaultAccount.user_id == test_user.id,
    ).first()
    assert vault_account.principal == deposit_amount - withdraw_amount
    
    # Verify user available balance increased
    user_available_balance = get_account_balance(db_session, available_account_id)
    expected_balance = initial_amount - deposit_amount + withdraw_amount
    assert user_available_balance == expected_balance, \
        f"Expected {expected_balance}, got {user_available_balance}"


def test_flex_withdraw_when_insufficient_creates_pending(client: TestClient, test_user: User, db_session):
    """
    Test FLEX withdraw when insufficient cash creates PENDING request
    """
    # Create token
    from app.api.v1.auth import create_access_token
    token = create_access_token(test_user.id, test_user.email)
    
    # Ensure wallet accounts exist
    wallet_accounts = ensure_wallet_accounts(db_session, test_user.id, "AED")
    available_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
    
    # Create initial balance
    operation = Operation(
        type=OperationType.DEPOSIT_AED,
        status=OperationStatus.COMPLETED,
        metadata={"test": "initial_balance"},
    )
    db_session.add(operation)
    db_session.flush()
    
    initial_amount = Decimal("10000.00")
    credit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=available_account_id,
        amount=initial_amount,
        currency="AED",
        entry_type=LedgerEntryType.CREDIT,
    )
    db_session.add(credit_entry)
    db_session.commit()
    
    # Create FLEX vault
    flex_vault = Vault(
        code="FLEX",
        name="Flexible Vault",
        status=VaultStatus.ACTIVE,
    )
    db_session.add(flex_vault)
    db_session.commit()
    
    # Deposit to FLEX
    deposit_amount = Decimal("1000.00")
    deposit_response = client.post(
        f"/api/v1/vaults/FLEX/deposits",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "amount": str(deposit_amount),
            "currency": "AED",
        },
    )
    assert deposit_response.status_code == 201
    
    # Try to withdraw more than pool has
    withdraw_amount = Decimal("2000.00")
    withdraw_response = client.post(
        f"/api/v1/vaults/FLEX/withdrawals",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "amount": str(withdraw_amount),
            "currency": "AED",
        },
    )
    
    assert withdraw_response.status_code == 201
    data = withdraw_response.json()
    assert data["status"] == "PENDING"
    assert "operation_id" not in data or data.get("operation_id") is None
    
    # Verify withdrawal request was created
    withdrawal_request = db_session.query(WithdrawalRequest).filter(
        WithdrawalRequest.vault_id == flex_vault.id,
        WithdrawalRequest.user_id == test_user.id,
        WithdrawalRequest.status == WithdrawalRequestStatus.PENDING,
    ).first()
    assert withdrawal_request is not None
    assert withdrawal_request.amount == withdraw_amount


def test_wallet_matrix_shows_flex_in_available_avenir_in_locked(client: TestClient, test_user: User, db_session):
    """
    Test wallet-matrix shows FLEX in available column and AVENIR in locked column
    """
    # Mock dev mode
    import app.api.v1.dev as dev_module
    original_check = dev_module.check_dev_mode
    dev_module.check_dev_mode = lambda: None
    
    # Create token
    from app.api.v1.auth import create_access_token
    token = create_access_token(test_user.id, test_user.email)
    
    # Ensure wallet accounts exist
    wallet_accounts = ensure_wallet_accounts(db_session, test_user.id, "AED")
    available_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
    
    # Create initial balance
    operation = Operation(
        type=OperationType.DEPOSIT_AED,
        status=OperationStatus.COMPLETED,
        metadata={"test": "initial_balance"},
    )
    db_session.add(operation)
    db_session.flush()
    
    initial_amount = Decimal("20000.00")
    credit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=available_account_id,
        amount=initial_amount,
        currency="AED",
        entry_type=LedgerEntryType.CREDIT,
    )
    db_session.add(credit_entry)
    db_session.commit()
    
    # Create vaults
    flex_vault = Vault(code="FLEX", name="Flexible Vault", status=VaultStatus.ACTIVE)
    avenir_vault = Vault(code="AVENIR", name="Avenir Vault", status=VaultStatus.ACTIVE)
    db_session.add(flex_vault)
    db_session.add(avenir_vault)
    db_session.commit()
    
    # Deposit to FLEX
    flex_deposit = Decimal("5000.00")
    flex_response = client.post(
        f"/api/v1/vaults/FLEX/deposits",
        headers={"Authorization": f"Bearer {token}"},
        json={"amount": str(flex_deposit), "currency": "AED"},
    )
    assert flex_response.status_code == 201
    
    # Deposit to AVENIR
    avenir_deposit = Decimal("3000.00")
    avenir_response = client.post(
        f"/api/v1/vaults/AVENIR/deposits",
        headers={"Authorization": f"Bearer {token}"},
        json={"amount": str(avenir_deposit), "currency": "AED"},
    )
    assert avenir_response.status_code == 201
    
    # Call wallet-matrix
    matrix_response = client.get(
        "/api/v1/dev/wallet-matrix",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Restore original check
    dev_module.check_dev_mode = original_check
    
    assert matrix_response.status_code == 200
    data = matrix_response.json()
    
    # Find FLEX row
    flex_rows = [r for r in data["rows"] if r.get("vault_id") == str(flex_vault.id)]
    assert len(flex_rows) == 1
    flex_row = flex_rows[0]
    assert flex_row["row_kind"] == "VAULT_USER"
    assert flex_row["available"] == "5000.00"
    assert flex_row["locked"] == "0.00"
    
    # Find AVENIR row
    avenir_rows = [r for r in data["rows"] if r.get("vault_id") == str(avenir_vault.id)]
    assert len(avenir_rows) == 1
    avenir_row = avenir_rows[0]
    assert avenir_row["row_kind"] == "VAULT_USER"
    assert avenir_row["available"] == "0.00"
    assert avenir_row["locked"] == "3000.00"  # From wallet_locks, not principal
    
    # Verify AED row locked is still 0
    aed_row = [r for r in data["rows"] if r["row_kind"] == "USER_AED"][0]
    assert aed_row["locked"] == "0.00"

