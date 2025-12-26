"""
Smoke tests for Wallet Matrix endpoint - Business invariants and canonical rules
"""
import pytest
from fastapi.testclient import TestClient
from decimal import Decimal
from uuid import uuid4

from app.core.offers.models import Offer, OfferStatus, InvestmentIntent, InvestmentIntentStatus
from app.core.vaults.models import Vault, VaultStatus, VaultAccount
from app.core.users.models import User, UserStatus
from app.services.wallet_helpers import ensure_wallet_accounts


def test_wallet_matrix_aed_locked_always_zero(client: TestClient, test_user: User, db_session):
    """
    SMOKE TEST: AED(USER).locked MUST always be "0.00"
    
    This is a canonical business rule: locked/vested amounts are attributed to instruments,
    not to the AED row. Even if WALLET_LOCKED has funds, they should appear in Offer/Vault rows.
    """
    # Mock dev mode
    import app.api.v1.dev as dev_module
    original_check = dev_module.check_dev_mode
    dev_module.check_dev_mode = lambda: None
    
    # Create token
    from app.api.v1.auth import create_access_token
    token = create_access_token(test_user.id, test_user.email)
    
    # Ensure wallet accounts exist (this creates WALLET_AVAILABLE, WALLET_BLOCKED, WALLET_LOCKED)
    ensure_wallet_accounts(db_session, test_user.id, "AED")
    
    # Make request
    response = client.get(
        "/api/v1/dev/wallet-matrix",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Restore original check
    dev_module.check_dev_mode = original_check
    
    assert response.status_code == 200
    data = response.json()
    
    # Find AED row
    aed_row = next((r for r in data["rows"] if r["row_kind"] == "USER_AED"), None)
    assert aed_row is not None, "AED row must exist"
    assert aed_row["label"] == "AED (USER)"
    
    # CANONICAL RULE: locked MUST be "0.00"
    assert aed_row["locked"] == "0.00", f"AED row locked must be 0.00, got {aed_row['locked']}"
    
    # Verify it's a string (not float)
    assert isinstance(aed_row["locked"], str)
    assert isinstance(aed_row["available"], str)
    assert isinstance(aed_row["blocked"], str)


def test_wallet_matrix_offer_row_appears_when_invested(client: TestClient, test_user: User, db_session):
    """
    SMOKE TEST: OFFER_USER row appears when user has invested, with correct locked amount
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
    
    # Create an offer
    offer = Offer(
        code="SMOKE-OFFER",
        name="Smoke Test Offer",
        currency="AED",
        max_amount=Decimal("100000.00"),
        invested_amount=Decimal("0.00"),
        committed_amount=Decimal("0.00"),
        status=OfferStatus.LIVE,
    )
    db_session.add(offer)
    db_session.flush()
    
    # Create investment intent (CONFIRMED) - this represents an active investment
    investment_amount = Decimal("7500.00")
    investment = InvestmentIntent(
        offer_id=offer.id,
        user_id=test_user.id,
        requested_amount=investment_amount,
        allocated_amount=investment_amount,
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
    
    # Find OFFER_USER row
    offer_rows = [r for r in data["rows"] if r["row_kind"] == "OFFER_USER"]
    assert len(offer_rows) > 0, "At least one OFFER_USER row must exist after investment"
    
    # Find the specific offer row
    offer_row = next((r for r in offer_rows if r["offer_id"] == str(offer.id)), None)
    assert offer_row is not None, f"OFFER_USER row for offer {offer.id} must exist"
    
    # Verify canonical mapping: investment goes to LOCKED column
    assert offer_row["locked"] == "7500.00", f"Offer row locked must be 7500.00, got {offer_row['locked']}"
    assert offer_row["available"] == "0.00", "Offer row available must be 0.00"
    assert offer_row["blocked"] == "0.00", "Offer row blocked must be 0.00"
    assert offer_row["position_principal"] == "7500.00", "Position principal must match invested amount"
    
    # Verify AED row locked is still 0.00 (anti-double-counting)
    aed_row = next((r for r in data["rows"] if r["row_kind"] == "USER_AED"), None)
    assert aed_row is not None
    assert aed_row["locked"] == "0.00", "AED row locked must remain 0.00 even after investment"


def test_wallet_matrix_vault_mapping_columns(client: TestClient, test_user: User, db_session):
    """
    SMOKE TEST: Vault positions mapped to correct columns (FLEX → available, AVENIR → locked)
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
    flex_principal = Decimal("100.00")
    avenir_principal = Decimal("200.00")
    
    vault_account_flex = VaultAccount(
        vault_id=vault_flex.id,
        user_id=test_user.id,
        principal=flex_principal,
        available_balance=flex_principal,
    )
    db_session.add(vault_account_flex)
    
    vault_account_avenir = VaultAccount(
        vault_id=vault_avenir.id,
        user_id=test_user.id,
        principal=avenir_principal,
        available_balance=avenir_principal,
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
    
    # Find VAULT_USER rows
    vault_rows = [r for r in data["rows"] if r["row_kind"] == "VAULT_USER"]
    assert len(vault_rows) == 2, "Two vault rows must exist (FLEX and AVENIR)"
    
    # Check FLEX vault: position goes to AVAILABLE column
    flex_row = next((r for r in vault_rows if r["vault_id"] == str(vault_flex.id)), None)
    assert flex_row is not None, "FLEX vault row must exist"
    assert flex_row["label"] == "COFFRE — FLEX"
    assert flex_row["available"] == "100.00", f"FLEX available must be 100.00, got {flex_row['available']}"
    assert flex_row["locked"] == "0.00", "FLEX locked must be 0.00"
    assert flex_row["blocked"] == "0.00", "FLEX blocked must be 0.00"
    
    # Check AVENIR vault: position goes to LOCKED column (vesting)
    avenir_row = next((r for r in vault_rows if r["vault_id"] == str(vault_avenir.id)), None)
    assert avenir_row is not None, "AVENIR vault row must exist"
    assert avenir_row["label"] == "COFFRE — AVENIR"
    assert avenir_row["available"] == "0.00", "AVENIR available must be 0.00"
    assert avenir_row["locked"] == "200.00", f"AVENIR locked must be 200.00, got {avenir_row['locked']}"
    assert avenir_row["blocked"] == "0.00", "AVENIR blocked must be 0.00"
    
    # Verify AED row locked is still 0.00 (anti-double-counting)
    aed_row = next((r for r in data["rows"] if r["row_kind"] == "USER_AED"), None)
    assert aed_row is not None
    assert aed_row["locked"] == "0.00", "AED row locked must remain 0.00 even with vault positions"


def test_wallet_matrix_no_double_counting(client: TestClient, test_user: User, db_session):
    """
    SMOKE TEST: Verify no double-counting between AED row and instrument rows
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
    
    # Create offer and investment
    offer = Offer(
        code="DOUBLE-COUNT-TEST",
        name="Double Count Test Offer",
        currency="AED",
        max_amount=Decimal("100000.00"),
        invested_amount=Decimal("0.00"),
        committed_amount=Decimal("0.00"),
        status=OfferStatus.LIVE,
    )
    db_session.add(offer)
    db_session.flush()
    
    investment_amount = Decimal("5000.00")
    investment = InvestmentIntent(
        offer_id=offer.id,
        user_id=test_user.id,
        requested_amount=investment_amount,
        allocated_amount=investment_amount,
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
    
    # Get AED row
    aed_row = next((r for r in data["rows"] if r["row_kind"] == "USER_AED"), None)
    assert aed_row is not None
    
    # Get OFFER row
    offer_row = next((r for r in data["rows"] if r["row_kind"] == "OFFER_USER"), None)
    assert offer_row is not None
    
    # ANTI-DOUBLE-COUNTING: AED locked must be 0.00 even if offer has locked amount
    assert aed_row["locked"] == "0.00", "AED locked must be 0.00 (amounts shown in instrument rows)"
    assert offer_row["locked"] == "5000.00", "Offer locked must show the invested amount"
    
    # The investment amount should NOT appear in AED row locked
    # This ensures the display is a "decomposition" not a "sum"

