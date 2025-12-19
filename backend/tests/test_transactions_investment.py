"""
Test that investment transactions appear in GET /api/v1/transactions
"""

import pytest
from uuid import uuid4
from decimal import Decimal
from sqlalchemy.orm import Session

from app.core.transactions.models import Transaction, TransactionType, TransactionStatus
from app.core.ledger.models import Operation, OperationType, OperationStatus
from app.core.offers.models import Offer, OfferStatus, OfferInvestment, OfferInvestmentStatus
from app.core.users.models import User
from app.services.offers.service import invest_in_offer
from app.services.wallet_helpers import ensure_wallet_accounts, get_account_balance
from app.core.accounts.models import AccountType


def test_investment_transaction_appears_in_list(
    db_session: Session,
    test_user: User,
):
    """
    Test that investment transactions appear in GET /api/v1/transactions.
    
    Scenario:
    1. Create a deposit transaction (existing)
    2. Create an offer and invest in it
    3. Call GET /api/v1/transactions
    4. Assert latest list contains INVESTMENT transaction with:
       - amount > 0
       - metadata with offer_name and offer_code
    """
    user_id = test_user.id
    currency = "AED"
    
    # Ensure wallet accounts exist
    ensure_wallet_accounts(db_session, user_id, currency)
    wallet_accounts = ensure_wallet_accounts(db_session, user_id, currency)
    available_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
    
    # Add some balance to AVAILABLE (simulate deposit)
    from app.core.ledger.models import LedgerEntry, LedgerEntryType
    from app.services.fund_services import lock_funds_for_investment
    
    # Create a simple deposit operation to add balance
    deposit_op = Operation(
        type=OperationType.DEPOSIT_AED,
        status=OperationStatus.COMPLETED,
    )
    db_session.add(deposit_op)
    db_session.flush()
    
    # Add ledger entry to AVAILABLE
    deposit_entry = LedgerEntry(
        operation_id=deposit_op.id,
        account_id=available_account_id,
        amount=Decimal("10000.00"),
        currency=currency,
        entry_type=LedgerEntryType.CREDIT,
    )
    db_session.add(deposit_entry)
    db_session.flush()
    
    # Create deposit transaction
    deposit_txn = Transaction(
        user_id=user_id,
        type=TransactionType.DEPOSIT,
        status=TransactionStatus.AVAILABLE,
        transaction_metadata={"currency": currency},
    )
    db_session.add(deposit_txn)
    db_session.flush()
    
    # Create an offer
    offer = Offer(
        code="TEST-OFFER-001",
        name="Test Offer",
        description="Test offer for transaction test",
        currency=currency,
        max_amount=Decimal("5000.00"),
        committed_amount=Decimal("0"),
        status=OfferStatus.LIVE,
    )
    db_session.add(offer)
    db_session.flush()
    
    # Invest in the offer
    investment_amount = Decimal("2000.00")
    investment = invest_in_offer(
        db=db_session,
        user_id=user_id,
        offer_id=offer.id,
        amount=investment_amount,
        currency=currency,
        idempotency_key=f"test-{uuid4()}",
    )
    
    db_session.commit()
    
    # Verify investment transaction was created
    investment_txns = db_session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.type == TransactionType.INVESTMENT,
    ).order_by(Transaction.created_at.desc()).all()
    
    assert len(investment_txns) > 0, "Investment transaction should be created"
    investment_txn = investment_txns[0]
    
    # Verify transaction metadata
    assert investment_txn.transaction_metadata is not None
    assert investment_txn.transaction_metadata.get("offer_id") == str(offer.id)
    assert investment_txn.transaction_metadata.get("offer_code") == offer.code
    assert investment_txn.transaction_metadata.get("offer_name") == offer.name
    assert investment_txn.transaction_metadata.get("accepted_amount") == str(investment_amount)
    
    # Verify transaction status
    assert investment_txn.status == TransactionStatus.LOCKED
    
    # Now test the API endpoint logic (simulate what /api/v1/transactions does)
    from app.api.v1.transactions import _compute_transaction_amount
    
    # Compute amount for investment transaction
    computed_amount = _compute_transaction_amount(
        db=db_session,
        transaction_id=investment_txn.id,
        user_id=user_id,
        currency=currency,
        transaction_type=investment_txn.type,
        transaction_metadata=investment_txn.transaction_metadata,
    )
    
    # Amount should be > 0 (not zero)
    assert computed_amount > 0, f"Investment transaction amount should be > 0, got {computed_amount}"
    assert computed_amount == investment_amount, f"Amount should match investment amount {investment_amount}, got {computed_amount}"
    
    # Verify all user transactions (deposit + investment)
    all_txns = db_session.query(Transaction).filter(
        Transaction.user_id == user_id,
    ).order_by(Transaction.created_at.desc()).all()
    
    assert len(all_txns) >= 2, "Should have at least deposit and investment transactions"
    
    # Investment should be most recent
    latest_txn = all_txns[0]
    assert latest_txn.type == TransactionType.INVESTMENT, "Latest transaction should be INVESTMENT"
    assert latest_txn.transaction_metadata.get("offer_name") == offer.name

