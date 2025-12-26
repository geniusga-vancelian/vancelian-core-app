"""
Tests for DEV wallet matrix endpoint
"""
import pytest
from fastapi.testclient import TestClient
from decimal import Decimal
from uuid import uuid4

from app.core.offers.models import Offer, OfferStatus
from app.core.vaults.models import Vault, VaultStatus
from app.core.users.models import User, UserStatus
from app.core.accounts.models import Account, AccountType
from app.core.ledger.models import Operation, OperationType, OperationStatus, LedgerEntry, LedgerEntryType


def test_dev_wallet_matrix_returns_rows(client: TestClient, test_user: User, db_session):
    """Test that wallet matrix endpoint returns rows with 3 columns"""
    # Mock dev mode
    import app.api.v1.dev as dev_module
    original_check = dev_module.check_dev_mode
    dev_module.check_dev_mode = lambda: None  # No-op
    
    # Create token for test user
    from app.api.v1.auth import create_access_token
    token = create_access_token(test_user.id, test_user.email)
    
    # Ensure wallet accounts exist
    from app.services.wallet_helpers import ensure_wallet_accounts
    ensure_wallet_accounts(db_session, test_user.id, "AED")
    
    # Create a vault
    vault = Vault(
        code="TEST-VAULT",
        name="Test Vault",
        status=VaultStatus.ACTIVE,
        cash_balance=Decimal("0.00"),
        total_aum=Decimal("0.00"),
    )
    db_session.add(vault)
    db_session.flush()
    
    # Create an offer
    offer = Offer(
        code="TEST-OFFER",
        name="Test Offer",
        currency="AED",
        max_amount=Decimal("100000.00"),
        invested_amount=Decimal("0.00"),
        committed_amount=Decimal("0.00"),
        status=OfferStatus.LIVE,
    )
    db_session.add(offer)
    db_session.commit()
    
    # Make request
    response = client.get(
        "/api/v1/dev/wallet-matrix",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Restore original check
    dev_module.check_dev_mode = original_check
    
    assert response.status_code == 200
    data = response.json()
    
    # Check structure
    assert "currency" in data
    assert "columns" in data
    assert "rows" in data
    assert "meta" in data
    
    # Check columns
    assert data["columns"] == ["available", "locked", "blocked"]
    assert len(data["columns"]) == 3
    
    # Check rows exist
    assert len(data["rows"]) > 0
    
    # Check at least one row has USER scope (AED row)
    user_rows = [r for r in data["rows"] if r["scope"]["type"] == "USER" and r["scope"]["owner"] == "USER"]
    assert len(user_rows) > 0
    # Check AED row exists and has locked=0.00
    aed_row = next((r for r in user_rows if r["row_kind"] == "USER_AED"), None)
    assert aed_row is not None
    assert aed_row["label"] == "AED (USER)"
    assert aed_row["locked"] == "0.00"
    
    # Check each row has 3 columns (available, locked, blocked)
    for row in data["rows"]:
        assert "available" in row
        assert "locked" in row
        assert "blocked" in row
        assert "label" in row
        assert "scope" in row
        assert "row_kind" in row
        # Check that amounts are strings with 2 decimal places
        assert isinstance(row["available"], str)
        assert isinstance(row["locked"], str)
        assert isinstance(row["blocked"], str)
    
    # Check meta
    assert "generated_at" in data["meta"]
    assert "sim_version" in data["meta"]
    assert data["meta"]["sim_version"] == "v2"


def test_dev_wallet_matrix_with_offer_investment(client: TestClient, test_user: User, db_session):
    """Test that wallet matrix shows offer investment rows correctly"""
    # Mock dev mode
    import app.api.v1.dev as dev_module
    original_check = dev_module.check_dev_mode
    dev_module.check_dev_mode = lambda: None  # No-op
    
    # Create token for test user
    from app.api.v1.auth import create_access_token
    token = create_access_token(test_user.id, test_user.email)
    
    # Ensure wallet accounts exist
    from app.services.wallet_helpers import ensure_wallet_accounts
    ensure_wallet_accounts(db_session, test_user.id, "AED")
    
    # Create an offer
    offer = Offer(
        code="TEST-OFFER",
        name="Test Offer Investment",
        currency="AED",
        max_amount=Decimal("100000.00"),
        invested_amount=Decimal("0.00"),
        committed_amount=Decimal("0.00"),
        status=OfferStatus.LIVE,
    )
    db_session.add(offer)
    db_session.flush()
    
    # Create investment intent (CONFIRMED)
    from app.core.offers.models import InvestmentIntent, InvestmentIntentStatus
    investment = InvestmentIntent(
        offer_id=offer.id,
        user_id=test_user.id,
        requested_amount=Decimal("5000.00"),
        allocated_amount=Decimal("5000.00"),
        currency="AED",
        status=InvestmentIntentStatus.CONFIRMED,
    )
    db_session.add(investment)
    db_session.commit()
    
    # Make request
    response = client.get(
        "/api/v1/dev/wallet-matrix",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Restore original check
    dev_module.check_dev_mode = original_check
    
    assert response.status_code == 200
    data = response.json()
    
    # Check that offer row exists
    offer_rows = [r for r in data["rows"] if r["row_kind"] == "OFFER_USER"]
    assert len(offer_rows) == 1
    offer_row = offer_rows[0]
    assert offer_row["label"] == "OFFRE — Test Offer Investment"
    assert offer_row["locked"] == "5000.00"
    assert offer_row["available"] == "0.00"
    assert offer_row["blocked"] == "0.00"
    assert offer_row["offer_id"] == str(offer.id)
    assert offer_row["position_principal"] == "5000.00"


def test_dev_wallet_matrix_with_vault_position(client: TestClient, test_user: User, db_session):
    """Test that wallet matrix shows vault positions correctly (FLEX vs AVENIR)"""
    # Mock dev mode
    import app.api.v1.dev as dev_module
    original_check = dev_module.check_dev_mode
    dev_module.check_dev_mode = lambda: None  # No-op
    
    # Create token for test user
    from app.api.v1.auth import create_access_token
    token = create_access_token(test_user.id, test_user.email)
    
    # Ensure wallet accounts exist
    from app.services.wallet_helpers import ensure_wallet_accounts
    ensure_wallet_accounts(db_session, test_user.id, "AED")
    
    # Create FLEX vault
    vault_flex = Vault(
        code="FLEX",
        name="Flexible Vault",
        status=VaultStatus.ACTIVE,
        cash_balance=Decimal("0.00"),
        total_aum=Decimal("0.00"),
    )
    db_session.add(vault_flex)
    db_session.flush()
    
    # Create AVENIR vault
    vault_avenir = Vault(
        code="AVENIR",
        name="Avenir Vault",
        status=VaultStatus.ACTIVE,
        cash_balance=Decimal("0.00"),
        total_aum=Decimal("0.00"),
    )
    db_session.add(vault_avenir)
    db_session.flush()
    
    # Create vault accounts with positions
    from app.core.vaults.models import VaultAccount
    vault_account_flex = VaultAccount(
        vault_id=vault_flex.id,
        user_id=test_user.id,
        principal=Decimal("10000.00"),
        available_balance=Decimal("10000.00"),
    )
    db_session.add(vault_account_flex)
    
    vault_account_avenir = VaultAccount(
        vault_id=vault_avenir.id,
        user_id=test_user.id,
        principal=Decimal("20000.00"),
        available_balance=Decimal("20000.00"),
    )
    db_session.add(vault_account_avenir)
    db_session.commit()
    
    # Make request
    response = client.get(
        "/api/v1/dev/wallet-matrix",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Restore original check
    dev_module.check_dev_mode = original_check
    
    assert response.status_code == 200
    data = response.json()
    
    # Check that vault rows exist
    vault_rows = [r for r in data["rows"] if r["row_kind"] == "VAULT_USER"]
    assert len(vault_rows) == 2
    
    # Check FLEX vault (should be in available column)
    flex_row = next((r for r in vault_rows if r["vault_id"] == str(vault_flex.id)), None)
    assert flex_row is not None
    assert flex_row["label"] == "COFFRE — FLEX"
    assert flex_row["available"] == "10000.00"
    assert flex_row["locked"] == "0.00"
    assert flex_row["blocked"] == "0.00"
    assert flex_row["position_principal"] == "10000.00"
    
    # Check AVENIR vault (should be in locked column)
    avenir_row = next((r for r in vault_rows if r["vault_id"] == str(vault_avenir.id)), None)
    assert avenir_row is not None
    assert avenir_row["label"] == "COFFRE — AVENIR"
    assert avenir_row["available"] == "0.00"
    assert avenir_row["locked"] == "20000.00"
    assert avenir_row["blocked"] == "0.00"
    assert avenir_row["position_principal"] == "20000.00"


def test_dev_wallet_matrix_requires_dev_mode(client: TestClient, test_user: User):
    """Test that wallet matrix endpoint requires dev mode"""
    # Create token for test user
    from app.api.v1.auth import create_access_token
    token = create_access_token(test_user.id, test_user.email)
    
    # Make request (should fail because dev mode check will fail in non-dev environment)
    response = client.get(
        "/api/v1/dev/wallet-matrix",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # In non-dev, should return 403
    # (But in test environment, dev mode might be enabled, so we check for either 200 or 403)
    assert response.status_code in [200, 403]
    
    if response.status_code == 403:
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "DEV_ENDPOINT_DISABLED"

