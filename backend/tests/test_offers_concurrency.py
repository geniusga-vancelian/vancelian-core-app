"""
Concurrency tests for offers investment - Enterprise-grade safety
"""

import pytest
from uuid import uuid4
from decimal import Decimal
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.offers.models import Offer, OfferStatus, OfferInvestment
from app.core.transactions.models import Transaction, TransactionType
from app.services.offers.service import invest_in_offer
from app.services.wallet_helpers import ensure_wallet_accounts, get_account_balance
from app.core.accounts.models import AccountType
from app.core.ledger.models import LedgerEntry, LedgerEntryType


def test_concurrent_investments_never_exceed_max(
    db_session: Session,
    test_user_with_balance,
):
    """
    Test that concurrent investments NEVER exceed max_amount.
    
    Scenario:
    - Offer with max_amount = 10000
    - 10 users each try to invest 2000 concurrently
    - Expected: Only 5 investments accepted (5 * 2000 = 10000)
    - Total committed_amount MUST be exactly 10000 (never exceed)
    """
    user_id = test_user_with_balance.id
    currency = "AED"
    
    # Ensure wallet accounts exist and have balance
    ensure_wallet_accounts(db_session, user_id, currency)
    wallet_accounts = ensure_wallet_accounts(db_session, user_id, currency)
    available_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
    
    # Add balance to AVAILABLE (simulate deposit)
    from app.core.ledger.models import Operation, OperationType, OperationStatus
    
    deposit_op = Operation(
        type=OperationType.DEPOSIT_AED,
        status=OperationStatus.COMPLETED,
    )
    db_session.add(deposit_op)
    db_session.flush()
    
    # Add ledger entry to AVAILABLE (enough for all investments)
    deposit_entry = LedgerEntry(
        operation_id=deposit_op.id,
        account_id=available_account_id,
        amount=Decimal("50000.00"),  # More than enough
        currency=currency,
        entry_type=LedgerEntryType.CREDIT,
    )
    db_session.add(deposit_entry)
    db_session.flush()
    
    # Create offer with max_amount = 10000
    offer = Offer(
        code="CONCURRENT-TEST-001",
        name="Concurrency Test Offer",
        description="Test concurrent investments",
        currency=currency,
        max_amount=Decimal("10000.00"),
        committed_amount=Decimal("0"),
        status=OfferStatus.LIVE,
    )
    db_session.add(offer)
    db_session.flush()
    db_session.commit()
    
    # Create 10 users (simulate different users investing)
    from app.core.users.models import User
    
    users = []
    for i in range(10):
        user = User(
            email=f"test_concurrent_{i}@example.com",
        )
        db_session.add(user)
        db_session.flush()
        
        # Ensure wallet accounts for this user
        ensure_wallet_accounts(db_session, user.id, currency)
        user_wallet_accounts = ensure_wallet_accounts(db_session, user.id, currency)
        user_available_account_id = user_wallet_accounts[AccountType.WALLET_AVAILABLE.value]
        
        # Add balance to this user's AVAILABLE
        user_deposit_op = Operation(
            type=OperationType.DEPOSIT_AED,
            status=OperationStatus.COMPLETED,
        )
        db_session.add(user_deposit_op)
        db_session.flush()
        
        user_deposit_entry = LedgerEntry(
            operation_id=user_deposit_op.id,
            account_id=user_available_account_id,
            amount=Decimal("5000.00"),
            currency=currency,
            entry_type=LedgerEntryType.CREDIT,
        )
        db_session.add(user_deposit_entry)
        db_session.flush()
        
        users.append(user)
    
    db_session.commit()
    
    # Function to invest (will be called concurrently)
    def invest_for_user(user_id: UUID, offer_id: UUID, amount: Decimal):
        """Invest for a user in a new session"""
        from app.infrastructure.database import SessionLocal
        session = SessionLocal()
        try:
            investment, remaining_after = invest_in_offer(
                db=session,
                user_id=user_id,
                offer_id=offer_id,
                amount=amount,
                currency=currency,
                idempotency_key=f"concurrent-test-{user_id}-{uuid4()}",
            )
            session.commit()
            return investment, remaining_after
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    # Execute 10 concurrent investments (each user invests 2000)
    investments = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(invest_for_user, user.id, offer.id, Decimal("2000.00"))
            for user in users
        ]
        
        for future in as_completed(futures):
            try:
                investment, remaining_after = future.result()
                investments.append(investment)
            except Exception as e:
                # Some investments may fail (offer full, etc.)
                # That's expected - we just need to verify total doesn't exceed max
                pass
    
    # Refresh offer to get final committed_amount
    db_session.refresh(offer)
    
    # CRITICAL ASSERTION: committed_amount MUST be <= max_amount
    assert offer.committed_amount <= offer.max_amount, \
        f"committed_amount ({offer.committed_amount}) exceeded max_amount ({offer.max_amount})"
    
    # Verify accepted investments sum to committed_amount
    accepted_investments = [
        inv for inv in investments
        if inv.status.value == "ACCEPTED"
    ]
    
    total_accepted = sum(inv.accepted_amount for inv in accepted_investments)
    assert total_accepted == offer.committed_amount, \
        f"Sum of accepted_amount ({total_accepted}) != committed_amount ({offer.committed_amount})"
    
    # Verify we got exactly 5 accepted investments (5 * 2000 = 10000)
    assert len(accepted_investments) == 5, \
        f"Expected 5 accepted investments, got {len(accepted_investments)}"
    
    # Verify remaining_after is correct for last investment
    last_investment = accepted_investments[-1]
    assert last_investment.accepted_amount == Decimal("2000.00"), \
        "Last investment should be fully accepted"
    
    # Verify no investment exceeded remaining capacity
    for inv in accepted_investments:
        assert inv.accepted_amount <= Decimal("2000.00"), \
            f"Investment {inv.id} accepted_amount ({inv.accepted_amount}) > requested (2000)"


def test_auto_cap_last_investor(
    db_session: Session,
    test_user_with_balance,
):
    """
    Test that last investor is auto-capped to remaining capacity.
    
    Scenario:
    - Offer with max_amount = 10000
    - First investor: 6000 (accepted: 6000, remaining: 4000)
    - Second investor: 6000 (accepted: 4000, remaining: 0) <- AUTO-CAPPED
    """
    user_id = test_user_with_balance.id
    currency = "AED"
    
    # Ensure wallet accounts exist
    ensure_wallet_accounts(db_session, user_id, currency)
    wallet_accounts = ensure_wallet_accounts(db_session, user_id, currency)
    available_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
    
    # Add balance
    from app.core.ledger.models import Operation, OperationType, OperationStatus, LedgerEntry, LedgerEntryType
    
    deposit_op = Operation(
        type=OperationType.DEPOSIT_AED,
        status=OperationStatus.COMPLETED,
    )
    db_session.add(deposit_op)
    db_session.flush()
    
    deposit_entry = LedgerEntry(
        operation_id=deposit_op.id,
        account_id=available_account_id,
        amount=Decimal("20000.00"),
        currency=currency,
        entry_type=LedgerEntryType.CREDIT,
    )
    db_session.add(deposit_entry)
    db_session.flush()
    
    # Create offer
    offer = Offer(
        code="AUTO-CAP-TEST-001",
        name="Auto-Cap Test Offer",
        description="Test auto-cap on last investor",
        currency=currency,
        max_amount=Decimal("10000.00"),
        committed_amount=Decimal("0"),
        status=OfferStatus.LIVE,
    )
    db_session.add(offer)
    db_session.flush()
    db_session.commit()
    
    # First investment: 6000 (should be fully accepted)
    investment1, remaining_after1 = invest_in_offer(
        db=db_session,
        user_id=user_id,
        offer_id=offer.id,
        amount=Decimal("6000.00"),
        currency=currency,
        idempotency_key=f"auto-cap-test-1-{uuid4()}",
    )
    db_session.commit()
    
    assert investment1.accepted_amount == Decimal("6000.00"), \
        f"First investment should be fully accepted, got {investment1.accepted_amount}"
    assert remaining_after1 == Decimal("4000.00"), \
        f"Remaining after first investment should be 4000, got {remaining_after1}"
    
    # Refresh offer
    db_session.refresh(offer)
    assert offer.committed_amount == Decimal("6000.00"), \
        f"Offer committed_amount should be 6000, got {offer.committed_amount}"
    
    # Second investment: 6000 (should be auto-capped to 4000)
    investment2, remaining_after2 = invest_in_offer(
        db=db_session,
        user_id=user_id,
        offer_id=offer.id,
        amount=Decimal("6000.00"),
        currency=currency,
        idempotency_key=f"auto-cap-test-2-{uuid4()}",
    )
    db_session.commit()
    
    assert investment2.accepted_amount == Decimal("4000.00"), \
        f"Second investment should be auto-capped to 4000, got {investment2.accepted_amount}"
    assert investment2.requested_amount == Decimal("6000.00"), \
        f"Second investment requested_amount should still be 6000"
    assert remaining_after2 == Decimal("0.00"), \
        f"Remaining after second investment should be 0, got {remaining_after2}"
    
    # Refresh offer
    db_session.refresh(offer)
    assert offer.committed_amount == Decimal("10000.00"), \
        f"Offer committed_amount should be exactly 10000, got {offer.committed_amount}"
    assert offer.committed_amount == offer.max_amount, \
        "Offer should be exactly full"
    
    # Third investment attempt: should fail with OFFER_FULL
    from app.services.offers.service import OfferFullError
    
    with pytest.raises(OfferFullError):
        invest_in_offer(
            db=db_session,
            user_id=user_id,
            offer_id=offer.id,
            amount=Decimal("1000.00"),
            currency=currency,
            idempotency_key=f"auto-cap-test-3-{uuid4()}",
        )

