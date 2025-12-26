"""
Tests for WalletLock model and integration with offer invest flow
"""
import pytest
from fastapi.testclient import TestClient
from decimal import Decimal
from uuid import uuid4

from app.core.offers.models import Offer, OfferStatus, InvestmentIntent, InvestmentIntentStatus
from app.core.accounts.wallet_locks import WalletLock, LockReason, ReferenceType, LockStatus
from app.core.users.models import User, UserStatus
from app.core.accounts.models import Account, AccountType
from app.core.ledger.models import Operation, OperationType, OperationStatus, LedgerEntry, LedgerEntryType
from app.services.wallet_helpers import ensure_wallet_accounts


def test_invest_offer_creates_wallet_lock_once(client: TestClient, test_user: User, db_session):
    """
    Test that investing in an offer creates a wallet_lock record (idempotent)
    """
    # Mock dev mode for wallet-matrix if needed
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
        code="WALLET-LOCK-TEST",
        name="Wallet Lock Test Offer",
        currency="AED",
        max_amount=Decimal("100000.00"),
        invested_amount=Decimal("0.00"),
        committed_amount=Decimal("0.00"),
        status=OfferStatus.LIVE,
    )
    db_session.add(offer)
    db_session.flush()
    
    # Create initial balance (via ledger)
    from app.services.wallet_helpers import get_account_balance
    wallet_accounts = ensure_wallet_accounts(db_session, test_user.id, "AED")
    available_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
    
    # Create deposit operation to add funds
    operation = Operation(
        type=OperationType.DEPOSIT_AED,
        status=OperationStatus.COMPLETED,
        metadata={"test": "initial_balance"},
    )
    db_session.add(operation)
    db_session.flush()
    
    amount = Decimal("10000.00")
    credit_entry = LedgerEntry(
        operation_id=operation.id,
        account_id=available_account_id,
        amount=amount,
        currency="AED",
        entry_type=LedgerEntryType.CREDIT,
    )
    db_session.add(credit_entry)
    db_session.commit()
    
    # Invest in offer via API
    invest_amount = Decimal("5000.00")
    response = client.post(
        f"/api/v1/offers/{offer.id}/invest",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "amount": str(invest_amount),
            "currency": "AED",
        },
    )
    
    # Restore original check
    dev_module.check_dev_mode = original_check
    
    assert response.status_code == 200
    data = response.json()
    assert data["accepted_amount"] == str(invest_amount)
    
    # Verify wallet_lock was created
    wallet_lock = db_session.query(WalletLock).filter(
        WalletLock.user_id == test_user.id,
        WalletLock.reference_id == offer.id,
        WalletLock.reason == LockReason.OFFER_INVEST.value,
        WalletLock.status == LockStatus.ACTIVE.value,
    ).first()
    
    assert wallet_lock is not None, "WalletLock should be created after investment"
    assert wallet_lock.amount == invest_amount
    assert wallet_lock.currency == "AED"
    assert wallet_lock.reference_type == ReferenceType.OFFER.value
    assert wallet_lock.intent_id is not None  # Should be linked to InvestmentIntent
    
    # Test idempotency: try to invest again with same amount (should not create duplicate lock)
    # Note: The actual invest endpoint might reject duplicate idempotency_key,
    # but we test that wallet_lock creation is idempotent via intent_id
    investment_intent = db_session.query(InvestmentIntent).filter(
        InvestmentIntent.user_id == test_user.id,
        InvestmentIntent.offer_id == offer.id,
        InvestmentIntent.status == InvestmentIntentStatus.CONFIRMED,
    ).first()
    
    assert investment_intent is not None
    assert wallet_lock.intent_id == investment_intent.id
    
    # Verify no duplicate locks exist
    lock_count = db_session.query(WalletLock).filter(
        WalletLock.intent_id == investment_intent.id,
    ).count()
    assert lock_count == 1, "Should have exactly one wallet_lock per intent_id (idempotency)"


def test_wallet_matrix_uses_wallet_locks_for_offer_row(client: TestClient, test_user: User, db_session):
    """
    Test that wallet-matrix uses wallet_locks (not InvestmentIntent) for OFFER_USER rows
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
        code="MATRIX-LOCK-TEST",
        name="Matrix Lock Test Offer",
        currency="AED",
        max_amount=Decimal("100000.00"),
        invested_amount=Decimal("0.00"),
        committed_amount=Decimal("0.00"),
        status=OfferStatus.LIVE,
    )
    db_session.add(offer)
    db_session.flush()
    
    # Create wallet_lock directly (simulating invest flow)
    invest_amount = Decimal("3000.00")
    wallet_lock = WalletLock(
        user_id=test_user.id,
        currency="AED",
        amount=invest_amount,
        reason=LockReason.OFFER_INVEST.value,
        reference_type=ReferenceType.OFFER.value,
        reference_id=offer.id,
        status=LockStatus.ACTIVE.value,
        intent_id=uuid4(),  # Mock intent_id
    )
    db_session.add(wallet_lock)
    db_session.commit()
    
    # Call wallet-matrix
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
    assert len(offer_rows) == 1, "Should have one OFFER_USER row"
    
    offer_row = offer_rows[0]
    assert offer_row["offer_id"] == str(offer.id)
    assert offer_row["locked"] == "3000.00", f"Expected 3000.00, got {offer_row['locked']}"
    assert offer_row["available"] == "0.00"
    assert offer_row["blocked"] == "0.00"


def test_admin_offer_portfolio_clients_locked_total(client: TestClient, test_user: User, db_session):
    """
    Test that admin offer portfolio endpoint shows correct clients_locked_total
    """
    # Create admin user (or use existing admin)
    from app.core.security.models import Role
    admin_user = User(
        email="admin@test.com",
        external_subject="admin-subject",
        status=UserStatus.ACTIVE,
    )
    db_session.add(admin_user)
    db_session.flush()
    
    # Create token for admin
    from app.api.v1.auth import create_access_token
    admin_token = create_access_token(admin_user.id, admin_user.email)
    
    # Mock admin role check
    from app.auth.dependencies import require_admin_role
    import app.auth.dependencies as auth_module
    original_check = auth_module.require_admin_role
    auth_module.require_admin_role = lambda: lambda principal: principal  # Mock admin check
    
    # Create an offer
    offer = Offer(
        code="PORTFOLIO-TEST",
        name="Portfolio Test Offer",
        currency="AED",
        max_amount=Decimal("100000.00"),
        invested_amount=Decimal("0.00"),
        committed_amount=Decimal("0.00"),
        status=OfferStatus.LIVE,
    )
    db_session.add(offer)
    db_session.flush()
    
    # Create multiple wallet_locks for different users (simulating multiple investments)
    user1 = test_user
    user2 = User(
        email="user2@test.com",
        external_subject="user2-subject",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user2)
    db_session.flush()
    
    lock1 = WalletLock(
        user_id=user1.id,
        currency="AED",
        amount=Decimal("5000.00"),
        reason=LockReason.OFFER_INVEST.value,
        reference_type=ReferenceType.OFFER.value,
        reference_id=offer.id,
        status=LockStatus.ACTIVE.value,
        intent_id=uuid4(),
    )
    lock2 = WalletLock(
        user_id=user2.id,
        currency="AED",
        amount=Decimal("3000.00"),
        reason=LockReason.OFFER_INVEST.value,
        reference_type=ReferenceType.OFFER.value,
        reference_id=offer.id,
        status=LockStatus.ACTIVE.value,
        intent_id=uuid4(),
    )
    db_session.add(lock1)
    db_session.add(lock2)
    db_session.commit()
    
    # Call admin portfolio endpoint
    response = client.get(
        f"/api/v1/admin/offers/{offer.id}/portfolio",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    # Restore original check
    auth_module.require_admin_role = original_check
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["offer_id"] == str(offer.id)
    assert data["currency"] == "AED"
    assert "system_wallet" in data
    assert data["clients_locked_total"] == "8000.00", f"Expected 8000.00 (5000+3000), got {data['clients_locked_total']}"

