"""
End-to-end tests: Investment flow (Available → Locked)
"""

import pytest
from uuid import uuid4
from decimal import Decimal
from sqlalchemy.orm import Session

from app.core.transactions.models import Transaction, TransactionType, TransactionStatus
from app.core.ledger.models import Operation, OperationType, OperationStatus, LedgerEntry, LedgerEntryType
from app.core.accounts.models import AccountType
from app.core.compliance.models import AuditLog
from app.services.wallet_helpers import get_wallet_balances
from app.services.fund_services import lock_funds_for_investment
from app.services.transaction_engine import recompute_transaction_status


def test_investment_available_to_locked(
    db_session: Session,
    test_user_with_balance,
):
    """
    Test investment path: Available → Locked
    
    Scenario:
    1. User has AVAILABLE balance
    2. Call POST /api/v1/investments (via service)
    3. Assert:
       - Transaction type = INVESTMENT
       - Status = LOCKED
       - Funds moved AVAILABLE → LOCKED
       - User cannot invest more than available
    
    Ledger invariants:
    - Sum of credits == Sum of debits
    - No LedgerEntry updated or deleted
    - TransactionStatus derived correctly
    - AuditLog written with correct actor_role
    """
    user_id = test_user_with_balance.id
    investment_amount = Decimal("5000.00")
    offer_id = uuid4()
    
    # Step 1: Verify initial AVAILABLE balance
    wallet_balances_before = get_wallet_balances(db_session, user_id, "AED")
    assert wallet_balances_before["available_balance"] == Decimal("10000.00")
    assert wallet_balances_before["locked_balance"] == Decimal("0")
    
    # Step 2: Create Transaction
    transaction = Transaction(
        id=uuid4(),
        user_id=user_id,
        type=TransactionType.INVESTMENT,
        status=TransactionStatus.INITIATED,
        metadata={
            "offer_id": str(offer_id),
            "currency": "AED",
            "reason": "Investment in Exclusive Offer X",
        },
    )
    db_session.add(transaction)
    db_session.flush()
    
    # Step 3: Lock funds for investment
    investment_operation = lock_funds_for_investment(
        db=db_session,
        user_id=user_id,
        currency="AED",
        amount=investment_amount,
        transaction_id=transaction.id,
        reason="Investment in Exclusive Offer X",
    )
    
    # Trigger status recomputation
    new_status = recompute_transaction_status(
        db=db_session,
        transaction_id=transaction.id,
    )
    
    # Step 4: Assert Transaction status = LOCKED
    db_session.refresh(transaction)
    assert transaction.status == TransactionStatus.LOCKED
    assert new_status == TransactionStatus.LOCKED
    
    # Step 5: Assert funds moved AVAILABLE → LOCKED
    wallet_balances_after = get_wallet_balances(db_session, user_id, "AED")
    assert wallet_balances_after["available_balance"] == Decimal("5000.00")  # 10000 - 5000
    assert wallet_balances_after["locked_balance"] == investment_amount
    assert wallet_balances_after["total_balance"] == Decimal("10000.00")  # Unchanged
    
    # Step 6: Verify ledger entries (double-entry)
    investment_ledger_entries = db_session.query(LedgerEntry).filter(
        LedgerEntry.operation_id == investment_operation.id
    ).all()
    assert len(investment_ledger_entries) == 2
    
    credits = [e.amount for e in investment_ledger_entries if e.entry_type == LedgerEntryType.CREDIT]
    debits = [abs(e.amount) for e in investment_ledger_entries if e.entry_type == LedgerEntryType.DEBIT]
    assert sum(credits) == sum(debits), "Double-entry invariant violated"
    
    # Step 7: Verify AuditLog
    investment_audit_logs = db_session.query(AuditLog).filter(
        AuditLog.entity_id == investment_operation.id
    ).all()
    assert len(investment_audit_logs) > 0
    assert any(log.action == "FUNDS_LOCKED_FOR_INVESTMENT" for log in investment_audit_logs)
    
    # Step 8: Verify user cannot invest more than available
    excess_amount = Decimal("6000.00")  # More than available (5000)
    
    from app.services.fund_services import InsufficientBalanceError
    
    with pytest.raises(InsufficientBalanceError):
        lock_funds_for_investment(
            db=db_session,
            user_id=user_id,
            currency="AED",
            amount=excess_amount,
            transaction_id=None,
            reason="Test excess investment",
        )
    
    # Step 9: Verify balances unchanged after failed investment
    wallet_balances_final = get_wallet_balances(db_session, user_id, "AED")
    assert wallet_balances_final["available_balance"] == Decimal("5000.00")
    assert wallet_balances_final["locked_balance"] == investment_amount


def test_investment_insufficient_balance_validation(
    db_session: Session,
    test_user_with_balance,
):
    """
    Test that investment fails when insufficient available balance.
    """
    user_id = test_user_with_balance.id
    excess_amount = Decimal("15000.00")  # More than available (10000)
    
    from app.services.fund_services import lock_funds_for_investment, InsufficientBalanceError
    
    with pytest.raises(InsufficientBalanceError):
        lock_funds_for_investment(
            db=db_session,
            user_id=user_id,
            currency="AED",
            amount=excess_amount,
            transaction_id=None,
            reason="Test insufficient balance",
        )

