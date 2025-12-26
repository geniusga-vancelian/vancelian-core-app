"""
Hotfix tests for wallet-matrix 401/500 errors
"""
import pytest
from fastapi.testclient import TestClient
from decimal import Decimal

from app.core.users.models import User, UserStatus
from app.core.accounts.models import Account, AccountType
from app.core.ledger.models import Operation, OperationType, OperationStatus, LedgerEntry, LedgerEntryType
from app.services.wallet_helpers import ensure_wallet_accounts


def test_wallet_matrix_returns_200_with_token(client: TestClient, test_user: User, db_session):
    """
    Test that wallet-matrix returns 200 with valid token and includes AED(USER) row
    """
    # Mock dev mode
    import app.api.v1.dev as dev_module
    original_check = dev_module.check_dev_mode
    dev_module.check_dev_mode = lambda: None
    
    # Create token
    from app.api.v1.auth import create_access_token
    token = create_access_token(test_user.id, test_user.email)
    
    # Ensure wallet accounts exist
    ensure_wallet_accounts(db_session, test_user.id, "AED")
    
    # Call wallet-matrix
    response = client.get(
        "/api/v1/dev/wallet-matrix",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Restore original check
    dev_module.check_dev_mode = original_check
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    
    # Verify response structure
    assert "currency" in data
    assert "columns" in data
    assert "rows" in data
    assert "meta" in data
    
    # Verify AED row exists
    aed_rows = [r for r in data["rows"] if r["row_kind"] == "USER_AED"]
    assert len(aed_rows) == 1, "Should have exactly one AED(USER) row"
    
    aed_row = aed_rows[0]
    assert aed_row["label"] == "AED (USER)", f"Expected 'AED (USER)', got '{aed_row['label']}'"
    assert aed_row["locked"] == "0.00", "AED row locked must always be 0.00 (canonical rule)"
    assert "available" in aed_row
    assert "blocked" in aed_row
    # MAPPING RULE: AED shows available + blocked only, locked = 0
    assert Decimal(aed_row["available"]) >= Decimal("0.00"), "AED available must be >= 0"
    assert Decimal(aed_row["blocked"]) >= Decimal("0.00"), "AED blocked must be >= 0"


def test_wallet_matrix_returns_401_without_token(client: TestClient):
    """
    Test that wallet-matrix returns 401 with proper JSON format when token is missing
    """
    # Mock dev mode
    import app.api.v1.dev as dev_module
    original_check = dev_module.check_dev_mode
    dev_module.check_dev_mode = lambda: None
    
    # Call wallet-matrix without token
    response = client.get("/api/v1/dev/wallet-matrix")
    
    # Restore original check
    dev_module.check_dev_mode = original_check
    
    assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
    data = response.json()
    
    # Verify error format
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
    assert "trace_id" in data["error"] or "trace_id" in data  # trace_id might be at root or in error


def test_wallet_matrix_mapping_rules(client: TestClient, test_user: User, db_session):
    """
    Test that wallet-matrix enforces mapping rules:
    - AED(USER): AVAILABLE + BLOCKED only (LOCKED must show 0)
    - OFFER(user positions): LOCKED only (available + blocked = 0)
    - VAULT FLEX(user position): AVAILABLE only (locked + blocked = 0)
    - VAULT AVENIR(user position): LOCKED only (available + blocked = 0)
    """
    # Mock dev mode
    import app.api.v1.dev as dev_module
    original_check = dev_module.check_dev_mode
    dev_module.check_dev_mode = lambda: None
    
    # Create token
    from app.api.v1.auth import create_access_token
    token = create_access_token(test_user.id, test_user.email)
    
    # Ensure wallet accounts exist
    from app.services.wallet_helpers import ensure_wallet_accounts
    ensure_wallet_accounts(db_session, test_user.id, "AED")
    
    # Create FLEX vault and position
    from app.core.vaults.models import Vault, VaultAccount, VaultStatus
    flex_vault = db_session.query(Vault).filter(Vault.code == "FLEX").first()
    if not flex_vault:
        flex_vault = Vault(code="FLEX", name="Flexible Vault", status=VaultStatus.ACTIVE)
        db_session.add(flex_vault)
        db_session.flush()
    
    flex_account = db_session.query(VaultAccount).filter(
        VaultAccount.vault_id == flex_vault.id,
        VaultAccount.user_id == test_user.id,
    ).first()
    if not flex_account:
        flex_account = VaultAccount(
            vault_id=flex_vault.id,
            user_id=test_user.id,
            principal=Decimal("1000.00"),
            available_balance=Decimal("1000.00"),
        )
        db_session.add(flex_account)
        db_session.commit()
    
    # Create AVENIR vault and position with wallet_lock
    avenir_vault = db_session.query(Vault).filter(Vault.code == "AVENIR").first()
    if not avenir_vault:
        avenir_vault = Vault(code="AVENIR", name="Avenir Vault", status=VaultStatus.ACTIVE)
        db_session.add(avenir_vault)
        db_session.flush()
    
    avenir_account = db_session.query(VaultAccount).filter(
        VaultAccount.vault_id == avenir_vault.id,
        VaultAccount.user_id == test_user.id,
    ).first()
    if not avenir_account:
        avenir_account = VaultAccount(
            vault_id=avenir_vault.id,
            user_id=test_user.id,
            principal=Decimal("2000.00"),
            available_balance=Decimal("2000.00"),
        )
        db_session.add(avenir_account)
        db_session.flush()
        
        # Create wallet_lock for AVENIR
        from app.core.accounts.wallet_locks import WalletLock, LockReason, ReferenceType, LockStatus
        wallet_lock = WalletLock(
            user_id=test_user.id,
            currency="AED",
            amount=Decimal("2000.00"),
            reason=LockReason.VAULT_AVENIR_VESTING.value,
            reference_type=ReferenceType.VAULT.value,
            reference_id=avenir_vault.id,
            status=LockStatus.ACTIVE.value,
            intent_id=None,
            operation_id=None,  # Not needed for test
        )
        db_session.add(wallet_lock)
        db_session.commit()
    
    # Create offer with investment (wallet_lock)
    from app.core.offers.models import Offer, OfferStatus
    offer = db_session.query(Offer).filter(Offer.code == "TEST-OFFER-MAPPING").first()
    if not offer:
        offer = Offer(
            code="TEST-OFFER-MAPPING",
            name="Test Offer Mapping",
            currency="AED",
            max_amount=Decimal("100000.00"),
            invested_amount=Decimal("0.00"),
            committed_amount=Decimal("0.00"),
            status=OfferStatus.LIVE,
        )
        db_session.add(offer)
        db_session.flush()
        
        # Create wallet_lock for offer
        offer_lock = WalletLock(
            user_id=test_user.id,
            currency="AED",
            amount=Decimal("5000.00"),
            reason=LockReason.OFFER_INVEST.value,
            reference_type="OFFER",
            reference_id=offer.id,
            status=LockStatus.ACTIVE.value,
            intent_id=None,
            operation_id=None,  # Not needed for test
        )
        db_session.add(offer_lock)
        db_session.commit()
    
    # Call wallet-matrix
    response = client.get(
        "/api/v1/dev/wallet-matrix",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Restore original check
    dev_module.check_dev_mode = original_check
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    
    # Verify AED row mapping
    aed_row = [r for r in data["rows"] if r["row_kind"] == "USER_AED"][0]
    assert aed_row["locked"] == "0.00", "AED row locked must always be 0.00"
    assert Decimal(aed_row["available"]) >= Decimal("0.00"), "AED available must be >= 0"
    assert Decimal(aed_row["blocked"]) >= Decimal("0.00"), "AED blocked must be >= 0"
    
    # Verify FLEX vault row mapping
    flex_rows = [r for r in data["rows"] if r.get("vault_id") == str(flex_vault.id) and r["row_kind"] == "VAULT_USER"]
    if flex_rows:
        flex_row = flex_rows[0]
        assert flex_row["available"] == "1000.00", f"FLEX available should be 1000.00, got {flex_row['available']}"
        assert flex_row["locked"] == "0.00", f"FLEX locked must be 0.00, got {flex_row['locked']}"
        assert flex_row["blocked"] == "0.00", f"FLEX blocked must be 0.00, got {flex_row['blocked']}"
    
    # Verify AVENIR vault row mapping
    avenir_rows = [r for r in data["rows"] if r.get("vault_id") == str(avenir_vault.id) and r["row_kind"] == "VAULT_USER"]
    if avenir_rows:
        avenir_row = avenir_rows[0]
        assert avenir_row["available"] == "0.00", f"AVENIR available must be 0.00, got {avenir_row['available']}"
        assert avenir_row["locked"] == "2000.00", f"AVENIR locked should be 2000.00, got {avenir_row['locked']}"
        assert avenir_row["blocked"] == "0.00", f"AVENIR blocked must be 0.00, got {avenir_row['blocked']}"
    
    # Verify offer row mapping
    offer_rows = [r for r in data["rows"] if r.get("offer_id") == str(offer.id) and r["row_kind"] == "OFFER_USER"]
    if offer_rows:
        offer_row = offer_rows[0]
        assert offer_row["available"] == "0.00", f"Offer available must be 0.00, got {offer_row['available']}"
        assert offer_row["locked"] == "5000.00", f"Offer locked should be 5000.00, got {offer_row['locked']}"
        assert offer_row["blocked"] == "0.00", f"Offer blocked must be 0.00, got {offer_row['blocked']}"


def test_wallet_matrix_currency_validation(client: TestClient, test_user: User, db_session):
    """
    Test that wallet-matrix validates currency parameter and returns proper JSON errors
    """
    # Mock dev mode
    import app.api.v1.dev as dev_module
    original_check = dev_module.check_dev_mode
    dev_module.check_dev_mode = lambda: None
    
    # Create token
    from app.api.v1.auth import create_access_token
    token = create_access_token(test_user.id, test_user.email)
    
    # Ensure wallet accounts exist
    ensure_wallet_accounts(db_session, test_user.id, "AED")
    
    # Test with invalid currency (should return 400 with JSON error)
    # Include Origin header to trigger CORS middleware
    response = client.get(
        "/api/v1/dev/wallet-matrix?currency=INVALID123",
        headers={
            "Authorization": f"Bearer {token}",
            "Origin": "http://localhost:3000",  # Trigger CORS middleware
        },
    )
    
    # Restore original check
    dev_module.check_dev_mode = original_check
    
    # Should return 400 for invalid currency
    assert response.status_code == 400, f"Expected 400 for invalid currency, got {response.status_code}: {response.text}"
    data = response.json()
    
    # Verify error format
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
    assert "trace_id" in data["error"]
    
    # Verify CORS headers are present even on error (when Origin header is present)
    assert "access-control-allow-origin" in [h.lower() for h in response.headers.keys()] or \
           "Access-Control-Allow-Origin" in response.headers, \
           f"CORS headers should be present even on error responses. Headers: {list(response.headers.keys())}"


def test_wallet_matrix_always_returns_json_on_error(client: TestClient, test_user: User, db_session):
    """
    Test that wallet-matrix always returns JSON error format, never raw stack traces
    """
    # Mock dev mode
    import app.api.v1.dev as dev_module
    original_check = dev_module.check_dev_mode
    dev_module.check_dev_mode = lambda: None
    
    # Create token
    from app.api.v1.auth import create_access_token
    token = create_access_token(test_user.id, test_user.email)
    
    # Ensure wallet accounts exist
    ensure_wallet_accounts(db_session, test_user.id, "AED")
    
    # Call wallet-matrix (should succeed or return JSON error, never raw HTML/stack trace)
    response = client.get(
        "/api/v1/dev/wallet-matrix",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Restore original check
    dev_module.check_dev_mode = original_check
    
    # Response should be JSON (even if error)
    assert response.headers.get("content-type", "").startswith("application/json"), \
           f"Response should be JSON, got content-type: {response.headers.get('content-type')}"
    
    # Should be able to parse as JSON
    try:
        data = response.json()
        # If error, should have structured format
        if response.status_code >= 400:
            assert "error" in data or "detail" in data, \
                   f"Error response should have error/detail: {data}"
    except Exception as e:
        pytest.fail(f"Response should be valid JSON, but got: {response.text[:200]}")


def test_avenir_deposit_does_not_500(client: TestClient, test_user: User, db_session):
    """
    Test that AVENIR deposit does not return 500 (at minimum, should return proper error if conditions not met)
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
    
    # Create AVENIR vault if it doesn't exist
    from app.core.vaults.models import Vault, VaultStatus
    avenir_vault = db_session.query(Vault).filter(Vault.code == "AVENIR").first()
    if not avenir_vault:
        avenir_vault = Vault(
            code="AVENIR",
            name="Avenir Vault",
            status=VaultStatus.ACTIVE,
        )
        db_session.add(avenir_vault)
        db_session.commit()
    
    # Try deposit (should succeed or return proper error, not 500)
    response = client.post(
        f"/api/v1/vaults/AVENIR/deposits",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "amount": "100.00",
            "currency": "AED",
        },
    )
    
    # Should not be 500
    assert response.status_code != 500, f"Got 500 error: {response.text}"
    
    # If error, should have proper JSON format with trace_id
    if response.status_code >= 400:
        data = response.json()
        assert "error" in data or "detail" in data, f"Error response should have error/detail: {response.text}"
        # trace_id might be in error object or at root
        error_obj = data.get("error", data.get("detail", {}))
        if isinstance(error_obj, dict):
            assert "trace_id" in error_obj or "trace_id" in data, "Error should include trace_id"

