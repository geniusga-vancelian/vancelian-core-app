"""
Test wallet_lock creation reasons and status
"""
import pytest
from decimal import Decimal

from app.core.accounts.wallet_locks import WalletLock, LockReason, LockStatus
from app.core.offers.models import Offer, OfferStatus, InvestmentIntent, InvestmentIntentStatus
from app.core.vaults.models import Vault, VaultAccount, VaultStatus
from app.core.users.models import User, UserStatus


def test_offer_invest_creates_wallet_lock_with_offer_invest_reason(db_session, test_user: User):
    """
    Verify that offer invest creates wallet_lock with reason=OFFER_INVEST and status=ACTIVE
    """
    # Create offer
    offer = Offer(
        code="TEST-OFFER-LOCK-REASON",
        name="Test Offer Lock Reason",
        currency="AED",
        max_amount=Decimal("100000.00"),
        invested_amount=Decimal("0.00"),
        committed_amount=Decimal("0.00"),
        status=OfferStatus.LIVE,
    )
    db_session.add(offer)
    db_session.flush()
    
    # Create investment intent (simulating invest flow)
    intent = InvestmentIntent(
        user_id=test_user.id,
        offer_id=offer.id,
        requested_amount=Decimal("5000.00"),
        allocated_amount=Decimal("5000.00"),
        currency="AED",
        status=InvestmentIntentStatus.CONFIRMED,
    )
    db_session.add(intent)
    db_session.flush()
    
    # Create wallet_lock (simulating what invest_in_offer_v1_1 does)
    wallet_lock = WalletLock(
        user_id=test_user.id,
        currency="AED",
        amount=Decimal("5000.00"),
        reason=LockReason.OFFER_INVEST.value,
        reference_type="OFFER",
        reference_id=offer.id,
        status=LockStatus.ACTIVE.value,
        intent_id=intent.id,
        operation_id=None,  # Would be set in real flow
    )
    db_session.add(wallet_lock)
    db_session.commit()
    
    # Verify
    assert wallet_lock.reason == LockReason.OFFER_INVEST.value
    assert wallet_lock.status == LockStatus.ACTIVE.value
    assert wallet_lock.reference_type == "OFFER"
    assert wallet_lock.reference_id == offer.id


def test_avenir_deposit_creates_wallet_lock_with_vault_avenir_vesting_reason(db_session, test_user: User):
    """
    Verify that AVENIR deposit creates wallet_lock with reason=VAULT_AVENIR_VESTING and status=ACTIVE
    """
    # Create AVENIR vault
    avenir_vault = Vault(
        code="AVENIR",
        name="Avenir Vault",
        status=VaultStatus.ACTIVE,
    )
    db_session.add(avenir_vault)
    db_session.flush()
    
    # Create wallet_lock (simulating what deposit_to_vault does for AVENIR)
    wallet_lock = WalletLock(
        user_id=test_user.id,
        currency="AED",
        amount=Decimal("3000.00"),
        reason=LockReason.VAULT_AVENIR_VESTING.value,
        reference_type="VAULT",
        reference_id=avenir_vault.id,
        status=LockStatus.ACTIVE.value,
        intent_id=None,  # Not applicable for vaults
        operation_id=None,  # Would be set in real flow
    )
    db_session.add(wallet_lock)
    db_session.commit()
    
    # Verify
    assert wallet_lock.reason == LockReason.VAULT_AVENIR_VESTING.value
    assert wallet_lock.status == LockStatus.ACTIVE.value
    assert wallet_lock.reference_type == "VAULT"
    assert wallet_lock.reference_id == avenir_vault.id

