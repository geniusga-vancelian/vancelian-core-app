"""
Tests for system wallet helpers
"""
import pytest
from decimal import Decimal
from uuid import uuid4
from sqlalchemy.orm import Session
from app.core.accounts.models import Account, AccountType
from app.core.offers.models import Offer, OfferStatus
from app.core.vaults.models import Vault, VaultStatus
from app.services.system_wallet_helpers import (
    ensure_offer_system_wallet,
    ensure_vault_system_wallet,
    get_or_create_offer_pool_account,
    get_or_create_vault_pool_account,
    get_offer_system_wallet_balances,
    get_vault_system_wallet_balances,
)


def test_ensure_offer_system_wallet_creates_three_accounts(db_session: Session):
    """Test that ensure_offer_system_wallet creates 3 accounts with user_id=None and offer_id set"""
    # Create an offer
    offer = Offer(
        code=f"TEST-OFFER-{uuid4().hex[:8]}",
        name="Test Offer",
        currency="AED",
        max_amount=Decimal("100000.00"),
        status=OfferStatus.LIVE,
    )
    db_session.add(offer)
    db_session.flush()
    
    # Ensure system wallet
    wallet = ensure_offer_system_wallet(db_session, offer.id, "AED")
    
    # Check that 3 accounts were created
    assert "available" in wallet
    assert "locked" in wallet
    assert "blocked" in wallet
    
    # Verify accounts exist in DB
    available_account = db_session.query(Account).filter(Account.id == wallet["available"]).first()
    locked_account = db_session.query(Account).filter(Account.id == wallet["locked"]).first()
    blocked_account = db_session.query(Account).filter(Account.id == wallet["blocked"]).first()
    
    assert available_account is not None
    assert locked_account is not None
    assert blocked_account is not None
    
    # Verify account properties
    for account in [available_account, locked_account, blocked_account]:
        assert account.user_id is None  # System account
        assert account.offer_id == offer.id
        assert account.vault_id is None
        assert account.currency == "AED"
    
    # Verify account types
    assert available_account.account_type == AccountType.OFFER_POOL_AVAILABLE
    assert locked_account.account_type == AccountType.OFFER_POOL_LOCKED
    assert blocked_account.account_type == AccountType.OFFER_POOL_BLOCKED


def test_ensure_offer_system_wallet_idempotent(db_session: Session):
    """Test that calling ensure_offer_system_wallet twice does not create duplicates"""
    # Create an offer
    offer = Offer(
        code=f"TEST-OFFER-{uuid4().hex[:8]}",
        name="Test Offer",
        currency="AED",
        max_amount=Decimal("100000.00"),
        status=OfferStatus.LIVE,
    )
    db_session.add(offer)
    db_session.flush()
    
    # Call twice
    wallet1 = ensure_offer_system_wallet(db_session, offer.id, "AED")
    wallet2 = ensure_offer_system_wallet(db_session, offer.id, "AED")
    
    # Should return same account IDs
    assert wallet1["available"] == wallet2["available"]
    assert wallet1["locked"] == wallet2["locked"]
    assert wallet1["blocked"] == wallet2["blocked"]
    
    # Should have exactly 3 accounts (one per bucket)
    accounts_count = db_session.query(Account).filter(
        Account.offer_id == offer.id,
        Account.user_id.is_(None),
    ).count()
    assert accounts_count == 3


def test_ensure_vault_system_wallet_creates_vault_pool_cash_if_missing(db_session: Session):
    """Test that ensure_vault_system_wallet creates VAULT_POOL_CASH if missing + VAULT_POOL_LOCKED/BLOCKED"""
    # Create a vault
    vault = Vault(
        code=f"TEST-VAULT-{uuid4().hex[:8]}",
        name="Test Vault",
        status=VaultStatus.ACTIVE,
        cash_balance=Decimal("0.00"),
        total_aum=Decimal("0.00"),
    )
    db_session.add(vault)
    db_session.flush()
    
    # Ensure system wallet
    wallet = ensure_vault_system_wallet(db_session, vault.id, "AED")
    
    # Check that 3 accounts were created
    assert "available" in wallet
    assert "locked" in wallet
    assert "blocked" in wallet
    
    # Verify accounts exist in DB
    available_account = db_session.query(Account).filter(Account.id == wallet["available"]).first()
    locked_account = db_session.query(Account).filter(Account.id == wallet["locked"]).first()
    blocked_account = db_session.query(Account).filter(Account.id == wallet["blocked"]).first()
    
    assert available_account is not None
    assert locked_account is not None
    assert blocked_account is not None
    
    # Verify account properties
    for account in [available_account, locked_account, blocked_account]:
        assert account.user_id is None  # System account
        assert account.vault_id == vault.id
        assert account.offer_id is None
        assert account.currency == "AED"
    
    # Verify account types (VAULT_POOL_CASH is the available bucket)
    assert available_account.account_type == AccountType.VAULT_POOL_CASH
    assert locked_account.account_type == AccountType.VAULT_POOL_LOCKED
    assert blocked_account.account_type == AccountType.VAULT_POOL_BLOCKED


def test_ensure_vault_system_wallet_idempotent(db_session: Session):
    """Test that calling ensure_vault_system_wallet twice does not create duplicates"""
    # Create a vault
    vault = Vault(
        code=f"TEST-VAULT-{uuid4().hex[:8]}",
        name="Test Vault",
        status=VaultStatus.ACTIVE,
        cash_balance=Decimal("0.00"),
        total_aum=Decimal("0.00"),
    )
    db_session.add(vault)
    db_session.flush()
    
    # Call twice
    wallet1 = ensure_vault_system_wallet(db_session, vault.id, "AED")
    wallet2 = ensure_vault_system_wallet(db_session, vault.id, "AED")
    
    # Should return same account IDs
    assert wallet1["available"] == wallet2["available"]
    assert wallet1["locked"] == wallet2["locked"]
    assert wallet1["blocked"] == wallet2["blocked"]
    
    # Should have exactly 3 accounts (VAULT_POOL_CASH + VAULT_POOL_LOCKED + VAULT_POOL_BLOCKED)
    accounts_count = db_session.query(Account).filter(
        Account.vault_id == vault.id,
        Account.user_id.is_(None),
    ).count()
    assert accounts_count == 3


def test_get_offer_system_wallet_balances(db_session: Session):
    """Test getting balances for offer system wallet"""
    # Create an offer
    offer = Offer(
        code=f"TEST-OFFER-{uuid4().hex[:8]}",
        name="Test Offer",
        currency="AED",
        max_amount=Decimal("100000.00"),
        status=OfferStatus.LIVE,
    )
    db_session.add(offer)
    db_session.flush()
    
    # Get balances (should be 0 initially)
    balances = get_offer_system_wallet_balances(db_session, offer.id, "AED")
    
    assert balances["available"] == Decimal("0.00")
    assert balances["locked"] == Decimal("0.00")
    assert balances["blocked"] == Decimal("0.00")


def test_get_vault_system_wallet_balances(db_session: Session):
    """Test getting balances for vault system wallet"""
    # Create a vault
    vault = Vault(
        code=f"TEST-VAULT-{uuid4().hex[:8]}",
        name="Test Vault",
        status=VaultStatus.ACTIVE,
        cash_balance=Decimal("0.00"),
        total_aum=Decimal("0.00"),
    )
    db_session.add(vault)
    db_session.flush()
    
    # Get balances (should be 0 initially)
    balances = get_vault_system_wallet_balances(db_session, vault.id, "AED")
    
    assert balances["available"] == Decimal("0.00")
    assert balances["locked"] == Decimal("0.00")
    assert balances["blocked"] == Decimal("0.00")


def test_vault_pool_cash_uses_vault_system_wallet_available(db_session: Session):
    """Test that vault pool cash (VAULT_POOL_CASH) is used as the available bucket"""
    # Create a vault
    vault = Vault(
        code=f"TEST-VAULT-{uuid4().hex[:8]}",
        name="Test Vault",
        status=VaultStatus.ACTIVE,
        cash_balance=Decimal("0.00"),
        total_aum=Decimal("0.00"),
    )
    db_session.add(vault)
    db_session.flush()
    
    # Ensure system wallet
    wallet = ensure_vault_system_wallet(db_session, vault.id, "AED")
    
    # Verify that available account is VAULT_POOL_CASH (backward compatibility)
    available_account = db_session.query(Account).filter(Account.id == wallet["available"]).first()
    assert available_account.account_type == AccountType.VAULT_POOL_CASH


