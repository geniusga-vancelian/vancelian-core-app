"""
Tests for OFFERS v1.1 - Concurrency safety and transactional integrity
"""

import pytest
import os
import threading
from uuid import uuid4
from decimal import Decimal
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.offers.models import Offer, OfferStatus, InvestmentIntent, InvestmentIntentStatus
from app.core.accounts.models import Account, AccountType
from app.core.users.models import User
from app.services.offers.service_v1_1 import (
    invest_in_offer_v1_1,
    OfferFullError,
    OfferNotLiveError,
    OfferNotFoundError,
    OfferCurrencyMismatchError,
    OfferClosedError,
    InsufficientAvailableFundsError,
)
from app.services.fund_services import InsufficientBalanceError, ValidationError


# Create session factory from test engine (same as conftest)
test_db_url = os.environ.get("DATABASE_URL", "postgresql://vancelian:vancelian_password@postgres:5432/vancelian_core_test")
test_engine = create_engine(test_db_url)
SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, expire_on_commit=False)


@pytest.fixture
def setup_user_with_balance(db_session: Session):
    """Create a user with available balance"""
    from app.core.ledger.models import Operation, OperationType, OperationStatus, LedgerEntry, LedgerEntryType
    
    user = User(email=f"test_user_{uuid4()}@example.com", password_hash="hashed_password")
    db_session.add(user)
    db_session.flush()
    
    # Create wallet accounts (no balance field - balance is computed from LedgerEntries)
    available_account = Account(
        user_id=user.id,
        currency="AED",
        account_type=AccountType.WALLET_AVAILABLE,
    )
    locked_account = Account(
        user_id=user.id,
        currency="AED",
        account_type=AccountType.WALLET_LOCKED,
    )
    db_session.add_all([available_account, locked_account])
    db_session.flush()
    
    # Create initial balance via ledger entries (deposit 100000 AED)
    initial_balance = Decimal("100000.00")
    deposit_operation = Operation(
        type=OperationType.DEPOSIT_AED,
        status=OperationStatus.COMPLETED,
        operation_metadata={"test": "initial_balance"},
    )
    db_session.add(deposit_operation)
    db_session.flush()
    
    # Create ledger entries: CREDIT to AVAILABLE, DEBIT from INTERNAL_OMNIBUS
    # First, get or create INTERNAL_OMNIBUS account
    omnibus_account = db_session.query(Account).filter(
        Account.account_type == AccountType.INTERNAL_OMNIBUS,
        Account.currency == "AED"
    ).first()
    if not omnibus_account:
        omnibus_account = Account(
            user_id=None,
            currency="AED",
            account_type=AccountType.INTERNAL_OMNIBUS,
        )
        db_session.add(omnibus_account)
        db_session.flush()
    
    # CREDIT to user's AVAILABLE account
    credit_entry = LedgerEntry(
        account_id=available_account.id,
        operation_id=deposit_operation.id,
        entry_type=LedgerEntryType.CREDIT,
        amount=initial_balance,
        currency="AED",
    )
    # DEBIT from INTERNAL_OMNIBUS
    debit_entry = LedgerEntry(
        account_id=omnibus_account.id,
        operation_id=deposit_operation.id,
        entry_type=LedgerEntryType.DEBIT,
        amount=-initial_balance,  # Negative for DEBIT
        currency="AED",
    )
    db_session.add_all([credit_entry, debit_entry])
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def setup_live_offer(db_session: Session):
    """Create a LIVE offer"""
    offer = Offer(
        code=f"OFFER-{uuid4().hex[:8]}",
        name="Test Live Offer",
        description="A live offer for testing concurrency",
        currency="AED",
        max_amount=Decimal("10000.00"),
        invested_amount=Decimal("0.00"),
        committed_amount=Decimal("0.00"),
        status=OfferStatus.LIVE,
    )
    db_session.add(offer)
    db_session.commit()
    db_session.refresh(offer)
    return offer


def test_concurrent_investments_never_exceed_max(
    db_session: Session,
    setup_user_with_balance: User,
    setup_live_offer: Offer,
):
    """
    Test that concurrent investments do not exceed the offer's max_amount.
    Simulates 10 concurrent investments of 1000 AED each in an offer with max_amount=10000.
    Expected: Exactly 10 investments succeed, total invested_amount = 10000 (no overflow).
    """
    from app.core.ledger.models import Operation, OperationType, OperationStatus, LedgerEntry, LedgerEntryType
    
    # Setup phase (single thread) - create multiple users, one per investment
    offer_id = setup_live_offer.id
    investment_amount = Decimal("1000.00")
    num_investments = 10
    
    # Create N users with balance (one per thread to avoid wallet conflicts)
    user_ids = []
    for i in range(num_investments):
        user = User(email=f"test_user_{i}_{uuid4()}@example.com", password_hash="hashed_password")
        db_session.add(user)
        db_session.flush()
        
        # Create wallet accounts
        available_account = Account(
            user_id=user.id,
            currency="AED",
            account_type=AccountType.WALLET_AVAILABLE,
        )
        locked_account = Account(
            user_id=user.id,
            currency="AED",
            account_type=AccountType.WALLET_LOCKED,
        )
        db_session.add_all([available_account, locked_account])
        db_session.flush()
        
        # Fund AVAILABLE account via ledger
        initial_balance = Decimal("100000.00")
        deposit_operation = Operation(
            type=OperationType.DEPOSIT_AED,
            status=OperationStatus.COMPLETED,
            operation_metadata={"test": f"initial_balance_user_{i}"},
        )
        db_session.add(deposit_operation)
        db_session.flush()
        
        # Get or create INTERNAL_OMNIBUS account
        omnibus_account = db_session.query(Account).filter(
            Account.account_type == AccountType.INTERNAL_OMNIBUS,
            Account.currency == "AED"
        ).first()
        if not omnibus_account:
            omnibus_account = Account(
                user_id=None,
                currency="AED",
                account_type=AccountType.INTERNAL_OMNIBUS,
            )
            db_session.add(omnibus_account)
            db_session.flush()
        
        # Create ledger entries
        credit_entry = LedgerEntry(
            account_id=available_account.id,
            operation_id=deposit_operation.id,
            entry_type=LedgerEntryType.CREDIT,
            amount=initial_balance,
            currency="AED",
        )
        debit_entry = LedgerEntry(
            account_id=omnibus_account.id,
            operation_id=deposit_operation.id,
            entry_type=LedgerEntryType.DEBIT,
            amount=-initial_balance,
            currency="AED",
        )
        db_session.add_all([credit_entry, debit_entry])
        user_ids.append(user.id)
    
    db_session.commit()
    
    # Synchronization barrier so all threads start at the same time
    barrier = threading.Barrier(num_investments)
    
    def invest_once(thread_id: int):
        """Worker function - each thread gets its own session and user"""
        # Wait for all threads to be ready (synchronize start)
        barrier.wait()
        
        # Create a brand new session for this thread
        local_session = SessionLocal()
        try:
            # Call service - SELECT FOR UPDATE will lock the offer row
            intent, remaining = invest_in_offer_v1_1(
                db=local_session,
                user_id=user_ids[thread_id],  # Each thread uses a different user
                offer_id=offer_id,  # Pass ID, not ORM object
                amount=investment_amount,
                currency="AED",
                idempotency_key=f"concurrency-{thread_id}-{uuid4()}",
            )
            # Commit within the same transaction (lock is held until commit)
            local_session.commit()
            return {
                "success": True,
                "intent_id": str(intent.id),
                "allocated_amount": intent.allocated_amount,
                "status": intent.status.value,
                "remaining": remaining,
            }
        except Exception as e:
            local_session.rollback()
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
        finally:
            local_session.close()
    
    # Execute concurrent investments
    with ThreadPoolExecutor(max_workers=num_investments) as executor:
        futures = [executor.submit(invest_once, i) for i in range(num_investments)]
        # Wait for all futures to complete (preserve order for debugging)
        results = [f.result() for f in futures]
    
    # Count successful investments
    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    
    # Debug: print failed results
    if failed:
        print(f"\nDEBUG: {len(failed)} failed investments:")
        for f in failed:
            print(f"  - Error: {f.get('error_type')}: {f.get('error')}")
    if successful:
        print(f"\nDEBUG: {len(successful)} successful investments (showing first 3):")
        for s in successful[:3]:
            print(f"  - Allocated: {s.get('allocated_amount')}, Status: {s.get('status')}")
    
    # Open a fresh session to verify final state
    verify_session = SessionLocal()
    try:
        offer = verify_session.query(Offer).filter(Offer.id == offer_id).first()
        
        # Assertions
        assert len(successful) == num_investments, f"Expected {num_investments} successful investments, got {len(successful)}. Failed ({len(failed)}): {failed[:3] if failed else []}"
        assert len(failed) == 0, f"Expected 0 failed investments, got {len(failed)}: {failed[:3] if failed else []}"
        assert offer.invested_amount == offer.max_amount, f"Expected invested_amount={offer.max_amount}, got {offer.invested_amount}"
        assert offer.invested_amount <= offer.max_amount, "invested_amount MUST NEVER exceed max_amount"
        assert offer.max_amount - offer.invested_amount >= Decimal("0"), "remaining_amount MUST NEVER be negative"
        
        # Verify all intents are CONFIRMED
        confirmed_intents = verify_session.query(InvestmentIntent).filter(
            InvestmentIntent.offer_id == offer_id,
            InvestmentIntent.status == InvestmentIntentStatus.CONFIRMED
        ).all()
        assert len(confirmed_intents) == num_investments, f"Expected {num_investments} CONFIRMED intents, got {len(confirmed_intents)}"
        
        # Verify total allocated_amount matches invested_amount
        total_allocated = sum(intent.allocated_amount for intent in confirmed_intents)
        assert total_allocated == offer.invested_amount, f"Total allocated_amount ({total_allocated}) should equal invested_amount ({offer.invested_amount})"
    finally:
        verify_session.close()


def test_partial_allocation_on_last_investor(
    db_session: Session,
    setup_user_with_balance: User,
    setup_live_offer: Offer,
):
    """
    Test partial allocation when requested_amount > remaining_amount.
    Scenario: Offer has 5000 remaining, user requests 10000.
    Expected: allocated_amount = 5000 (partial fill), status = CONFIRMED.
    """
    offer = setup_live_offer
    user = setup_user_with_balance
    
    # First, invest 5000 to leave 5000 remaining
    intent1, remaining1 = invest_in_offer_v1_1(
        db=db_session,
        user_id=user.id,
        offer_id=offer.id,
        amount=Decimal("5000.00"),
        currency="AED",
        idempotency_key=f"test-{uuid4()}",
    )
    db_session.commit()
    
    assert intent1.status == InvestmentIntentStatus.CONFIRMED
    assert intent1.allocated_amount == Decimal("5000.00")
    assert remaining1 == Decimal("5000.00")
    
    # Now request 10000 (more than remaining)
    intent2, remaining2 = invest_in_offer_v1_1(
        db=db_session,
        user_id=user.id,
        offer_id=offer.id,
        amount=Decimal("10000.00"),
        currency="AED",
        idempotency_key=f"test-{uuid4()}",
    )
    db_session.commit()
    
    # Should get partial allocation
    assert intent2.status == InvestmentIntentStatus.CONFIRMED
    assert intent2.allocated_amount == Decimal("5000.00"), f"Expected allocated_amount=5000, got {intent2.allocated_amount}"
    assert intent2.requested_amount == Decimal("10000.00")
    assert remaining2 == Decimal("0.00"), f"Expected remaining=0, got {remaining2}"
    
    # Verify offer is now full
    db_session.refresh(offer)
    assert offer.invested_amount == offer.max_amount


def test_offer_full_rejection(
    db_session: Session,
    setup_user_with_balance: User,
    setup_live_offer: Offer,
):
    """
    Test that investment is rejected when remaining_amount == 0.
    """
    offer = setup_live_offer
    user = setup_user_with_balance
    
    # Fill the offer completely
    intent1, _ = invest_in_offer_v1_1(
        db=db_session,
        user_id=user.id,
        offer_id=offer.id,
        amount=offer.max_amount,
        currency="AED",
        idempotency_key=f"test-{uuid4()}",
    )
    db_session.commit()
    
    assert intent1.status == InvestmentIntentStatus.CONFIRMED
    
    # Refresh offer to get updated invested_amount
    db_session.refresh(offer)
    assert offer.max_amount - offer.invested_amount == Decimal("0.00")
    
    # Try to invest again (should fail with OFFER_FULL)
    # Note: The service creates a REJECTED intent before raising the exception
    try:
        invest_in_offer_v1_1(
            db=db_session,
            user_id=user.id,
            offer_id=offer.id,
            amount=Decimal("1000.00"),
            currency="AED",
            idempotency_key=f"test-{uuid4()}",
        )
        db_session.commit()
        assert False, "Should have raised OfferFullError"
    except OfferFullError:
        # Service creates REJECTED intent before raising, so commit it
        db_session.commit()
    
    # Verify intent was created with REJECTED status
    rejected_intent = db_session.query(InvestmentIntent).filter(
        InvestmentIntent.offer_id == offer.id,
        InvestmentIntent.status == InvestmentIntentStatus.REJECTED
    ).order_by(InvestmentIntent.created_at.desc()).first()
    
    assert rejected_intent is not None, "REJECTED intent should be created when offer is full"
    assert rejected_intent.allocated_amount == Decimal("0.00")


def test_idempotency(
    db_session: Session,
    setup_user_with_balance: User,
    setup_live_offer: Offer,
):
    """
    Test that idempotency_key prevents duplicate investments.
    """
    offer = setup_live_offer
    user = setup_user_with_balance
    idempotency_key = f"test-idempotency-{uuid4()}"
    
    # First investment
    intent1, remaining1 = invest_in_offer_v1_1(
        db=db_session,
        user_id=user.id,
        offer_id=offer.id,
        amount=Decimal("1000.00"),
        currency="AED",
        idempotency_key=idempotency_key,
    )
    db_session.commit()
    
    # Second investment with same idempotency_key (should return existing)
    intent2, remaining2 = invest_in_offer_v1_1(
        db=db_session,
        user_id=user.id,
        offer_id=offer.id,
        amount=Decimal("2000.00"),  # Different amount (should be ignored)
        currency="AED",
        idempotency_key=idempotency_key,
    )
    db_session.commit()
    
    # Should return the same intent
    assert intent1.id == intent2.id
    assert intent1.allocated_amount == intent2.allocated_amount
    
    # Verify only one intent exists
    intents = db_session.query(InvestmentIntent).filter(
        InvestmentIntent.idempotency_key == idempotency_key
    ).all()
    assert len(intents) == 1


def test_ledger_double_entry_invariant(
    db_session: Session,
    setup_user_with_balance: User,
    setup_live_offer: Offer,
):
    """
    Test that ledger entries maintain double-entry accounting invariants.
    After investment, sum of all ledger entries for the operation should be 0.
    """
    from app.core.ledger.models import LedgerEntry, LedgerEntryType
    from app.services.wallet_helpers import get_wallet_balances
    
    offer = setup_live_offer
    user = setup_user_with_balance
    investment_amount = Decimal("5000.00")
    
    intent, remaining = invest_in_offer_v1_1(
        db=db_session,
        user_id=user.id,
        offer_id=offer.id,
        amount=investment_amount,
        currency="AED",
        idempotency_key=f"test-{uuid4()}",
    )
    db_session.commit()
    
    assert intent.status == InvestmentIntentStatus.CONFIRMED
    assert intent.operation_id is not None
    
    # Get all ledger entries for this operation
    entries = db_session.query(LedgerEntry).filter(
        LedgerEntry.operation_id == intent.operation_id
    ).all()
    
    # Sum all entries (should be 0 for double-entry)
    total = sum(entry.amount for entry in entries)
    assert total == Decimal("0.00"), f"Ledger entries should sum to 0 (double-entry invariant), got {total}"
    
    # Verify funds moved from AVAILABLE to LOCKED using wallet helper
    wallet_balances = get_wallet_balances(db_session, user.id, "AED")
    assert wallet_balances["available_balance"] == Decimal("95000.00"), f"Expected AVAILABLE balance=95000, got {wallet_balances['available_balance']}"
    assert wallet_balances["locked_balance"] == investment_amount, f"Expected LOCKED balance={investment_amount}, got {wallet_balances['locked_balance']}"


def test_insufficient_funds_rejection(
    db_session: Session,
    setup_user_with_balance: User,
    setup_live_offer: Offer,
):
    """
    Test that investment is rejected when user has insufficient available funds.
    
    Scenario:
    - Offer max_amount = 10000, so allocated = min(requested, 10000)
    - User has 100000 available initially
    - We reduce user's available balance to 5000 (less than offer max)
    - User requests 10000, allocated would be 10000, but user only has 5000
    - Service should reject with InsufficientAvailableFundsError
    """
    from app.services.wallet_helpers import get_wallet_balances
    from app.core.ledger.models import LedgerEntry, LedgerEntryType
    from app.core.accounts.models import Account, AccountType
    
    offer = setup_live_offer
    user = setup_user_with_balance
    
    # Reduce user's available balance to 5000 (less than offer max of 10000)
    # by creating a debit entry
    available_account = db_session.query(Account).filter(
        Account.user_id == user.id,
        Account.account_type == AccountType.WALLET_AVAILABLE,
        Account.currency == "AED"
    ).first()
    
    # Create a debit of 95000 to leave 5000 available
    from app.core.ledger.models import Operation, OperationType, OperationStatus
    debit_operation = Operation(
        type=OperationType.ADJUSTMENT,
        status=OperationStatus.COMPLETED,
        operation_metadata={"test": "reduce_balance_for_insufficient_funds_test"},
    )
    db_session.add(debit_operation)
    db_session.flush()
    
    # Get INTERNAL_OMNIBUS account
    omnibus_account = db_session.query(Account).filter(
        Account.account_type == AccountType.INTERNAL_OMNIBUS,
        Account.currency == "AED"
    ).first()
    
    # Debit from user's AVAILABLE, credit to OMNIBUS
    debit_entry = LedgerEntry(
        account_id=available_account.id,
        operation_id=debit_operation.id,
        entry_type=LedgerEntryType.DEBIT,
        amount=Decimal("-95000.00"),  # Negative for DEBIT
        currency="AED",
    )
    credit_entry = LedgerEntry(
        account_id=omnibus_account.id,
        operation_id=debit_operation.id,
        entry_type=LedgerEntryType.CREDIT,
        amount=Decimal("95000.00"),
        currency="AED",
    )
    db_session.add_all([debit_entry, credit_entry])
    db_session.commit()
    
    # Verify user now has 5000 available (less than offer max of 10000)
    wallet_balances = get_wallet_balances(db_session, user.id, "AED")
    assert wallet_balances["available_balance"] == Decimal("5000.00"), f"Expected 5000 available, got {wallet_balances['available_balance']}"
    
    # Refresh offer to ensure it's in the session
    db_session.refresh(offer)
    assert offer.invested_amount == Decimal("0.00"), "Offer should start with 0 invested"
    
    # Try to invest 10000 (allocated would be 10000, but user only has 5000 available)
    # The service will:
    # 1. Lock offer, compute allocated = min(10000, 10000) = 10000
    # 2. Try to move 10000 from AVAILABLE to LOCKED
    # 3. lock_funds_for_investment will check balance: 5000 < 10000 -> raise InsufficientBalanceError
    # 4. Service catches it, marks intent REJECTED, and re-raises as InsufficientAvailableFundsError
    try:
        intent, remaining = invest_in_offer_v1_1(
            db=db_session,
            user_id=user.id,
            offer_id=offer.id,
            amount=Decimal("10000.00"),  # Request 10000, allocated will be 10000, but user only has 5000
            currency="AED",
            idempotency_key=f"test-{uuid4()}",
        )
        # If no exception, check if intent was rejected
        db_session.commit()
        # This should not happen - user should not have enough for the allocated amount
        if intent.status == InvestmentIntentStatus.REJECTED:
            # Intent was rejected but no exception was raised (unexpected but acceptable)
            pass
        else:
            assert False, f"Should have raised InsufficientAvailableFundsError but got intent status {intent.status}"
    except (InsufficientBalanceError, InsufficientAvailableFundsError) as e:
        # Service creates REJECTED intent before raising, so commit it
        db_session.commit()
    
    # Verify intent was created with REJECTED status
    rejected_intent = db_session.query(InvestmentIntent).filter(
        InvestmentIntent.offer_id == offer.id,
        InvestmentIntent.status == InvestmentIntentStatus.REJECTED
    ).order_by(InvestmentIntent.created_at.desc()).first()
    
    assert rejected_intent is not None, "REJECTED intent should be created when insufficient funds"
    assert rejected_intent.allocated_amount == Decimal("0.00")
    
    # Verify offer.invested_amount unchanged
    db_session.refresh(offer)
    assert offer.invested_amount == Decimal("0.00"), "Offer invested_amount should not change when funds insufficient"


def test_offer_closed_rejection(
    db_session: Session,
    setup_user_with_balance: User,
):
    """
    Test that investment is rejected when offer is CLOSED.
    """
    user = setup_user_with_balance
    
    # Create a CLOSED offer
    offer = Offer(
        code=f"OFFER-{uuid4().hex[:8]}",
        name="Closed Offer",
        description="A closed offer",
        currency="AED",
        max_amount=Decimal("10000.00"),
        invested_amount=Decimal("0.00"),
        committed_amount=Decimal("0.00"),
        status=OfferStatus.CLOSED,
    )
    db_session.add(offer)
    db_session.commit()
    db_session.refresh(offer)
    
    # Try to invest (should fail with OFFER_CLOSED)
    # Note: The service creates a REJECTED intent before raising the exception
    try:
        invest_in_offer_v1_1(
            db=db_session,
            user_id=user.id,
            offer_id=offer.id,
            amount=Decimal("1000.00"),
            currency="AED",
            idempotency_key=f"test-{uuid4()}",
        )
        db_session.commit()
        assert False, "Should have raised OfferClosedError"
    except OfferClosedError:
        # Service creates REJECTED intent before raising, so commit it
        db_session.commit()
    
    # Verify intent was created with REJECTED status
    rejected_intent = db_session.query(InvestmentIntent).filter(
        InvestmentIntent.offer_id == offer.id,
        InvestmentIntent.status == InvestmentIntentStatus.REJECTED
    ).first()
    
    assert rejected_intent is not None, "REJECTED intent should be created when offer is CLOSED"


def test_invest_255_aed_regression(db_session: Session, setup_user_with_balance):
    """
    Regression test for the 500 error fix (amount=255 AED).
    
    This test ensures that:
    - Investment with amount=255 AED works correctly
    - InvestmentIntent is created with CONFIRMED status
    - Ledger movement AVAILABLE -> LOCKED is correct
    - invested_amount is increased by allocated_amount
    - created_at is automatically set by the database
    """
    user, available_account, locked_account = setup_user_with_balance(db_session)
    
    # Create a LIVE offer with enough capacity
    offer = Offer(
        code="REGRESSION-TEST-001",
        name="Regression Test Offer",
        description="Test offer for 255 AED investment",
        currency="AED",
        max_amount=Decimal("100000.00"),
        invested_amount=Decimal("0.00"),
        committed_amount=Decimal("0.00"),
        status=OfferStatus.LIVE,
    )
    db_session.add(offer)
    db_session.commit()
    db_session.refresh(offer)
    
    # Invest 255 AED
    investment_amount = Decimal("255.00")
    idempotency_key = f"regression-test-{uuid4()}"
    
    intent, remaining_after = invest_in_offer_v1_1(
        db=db_session,
        user_id=user.id,
        offer_id=offer.id,
        amount=investment_amount,
        currency="AED",
        idempotency_key=idempotency_key,
    )
    
    db_session.commit()
    db_session.refresh(intent)
    db_session.refresh(offer)
    
    # Verify InvestmentIntent
    assert intent.status == InvestmentIntentStatus.CONFIRMED, "Intent should be CONFIRMED"
    assert intent.allocated_amount == investment_amount, f"Allocated amount should be {investment_amount}"
    assert intent.requested_amount == investment_amount, f"Requested amount should be {investment_amount}"
    assert intent.created_at is not None, "created_at should be automatically set by database"
    assert intent.operation_id is not None, "operation_id should be set for CONFIRMED intent"
    
    # Verify offer.invested_amount increased
    assert offer.invested_amount == investment_amount, f"Offer invested_amount should be {investment_amount}"
    
    # Verify remaining_after
    expected_remaining = offer.max_amount - investment_amount
    assert remaining_after == expected_remaining, f"Remaining should be {expected_remaining}"
    
    # Verify ledger movement: AVAILABLE -> LOCKED
    from app.core.ledger.models import LedgerEntry, LedgerEntryType
    
    available_entries = db_session.query(LedgerEntry).filter(
        LedgerEntry.account_id == available_account.id,
        LedgerEntry.operation_id == intent.operation_id
    ).all()
    
    locked_entries = db_session.query(LedgerEntry).filter(
        LedgerEntry.account_id == locked_account.id,
        LedgerEntry.operation_id == intent.operation_id
    ).all()
    
    # AVAILABLE account should have a negative entry (debit)
    available_debit = sum(entry.amount for entry in available_entries if entry.amount < 0)
    assert available_debit == -investment_amount, f"AVAILABLE should be debited by {investment_amount}"
    
    # LOCKED account should have a positive entry (credit)
    locked_credit = sum(entry.amount for entry in locked_entries if entry.amount > 0)
    assert locked_credit == investment_amount, f"LOCKED should be credited by {investment_amount}"
    
    # Verify double-entry: total debits == total credits
    total_debits = abs(available_debit)
    total_credits = locked_credit
    assert total_debits == total_credits, "Ledger must maintain double-entry accounting"
