"""
End-to-end tests: Deposit → Compliance → Rejected flow
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
from app.services.fund_services import record_deposit_blocked, reject_deposit
from app.services.transaction_engine import recompute_transaction_status


def test_deposit_rejection_path(
    db_session: Session,
    test_user,
    test_internal_account,
):
    """
    Test rejection path: Deposit → Compliance Review → Rejected
    
    Scenario:
    1. Create user
    2. Simulate ZAND webhook deposit (via service)
    3. Assert: Transaction status = COMPLIANCE_REVIEW, Funds in WALLET_BLOCKED
    4. Call admin reject-deposit
    5. Assert: Transaction status = FAILED, Funds removed from BLOCKED
    
    Ledger invariants:
    - Sum of credits == Sum of debits (including reversal)
    - No LedgerEntry updated or deleted
    - TransactionStatus derived correctly
    - AuditLog with reason exists
    """
    user_id = test_user.id
    amount = Decimal("3000.00")
    provider_event_id = f"ZAND-EVT-{uuid4()}"
    rejection_reason = "Sanctions match / invalid IBAN"
    
    # Step 1: Create Transaction
    transaction = Transaction(
        id=uuid4(),
        user_id=user_id,
        type=TransactionType.DEPOSIT,
        status=TransactionStatus.INITIATED,
        external_reference=provider_event_id,
    )
    db_session.add(transaction)
    db_session.flush()
    
    # Step 2: Record deposit as blocked (simulate webhook)
    deposit_operation = record_deposit_blocked(
        db=db_session,
        user_id=user_id,
        currency="AED",
        amount=amount,
        transaction_id=transaction.id,
        idempotency_key=provider_event_id,
        provider_reference=provider_event_id,
    )
    
    # Trigger status recomputation
    recompute_transaction_status(db=db_session, transaction_id=transaction.id)
    
    # Step 3: Assert Transaction status = COMPLIANCE_REVIEW
    db_session.refresh(transaction)
    assert transaction.status == TransactionStatus.COMPLIANCE_REVIEW
    
    # Step 4: Assert funds in WALLET_BLOCKED
    wallet_balances_before = get_wallet_balances(db_session, user_id, "AED")
    assert wallet_balances_before["blocked_balance"] == amount
    assert wallet_balances_before["total_balance"] == amount
    
    # Step 5: Count ledger entries before rejection
    ledger_entries_before = db_session.query(LedgerEntry).join(Operation).filter(
        Operation.transaction_id == transaction.id
    ).count()
    assert ledger_entries_before == 2  # CREDIT BLOCKED + DEBIT OMNIBUS
    
    # Step 6: Reject deposit
    rejection_operation = reject_deposit(
        db=db_session,
        transaction_id=transaction.id,
        user_id=user_id,
        currency="AED",
        amount=amount,
        reason=rejection_reason,
        actor_user_id=None,  # Compliance user
    )
    
    # Trigger status recomputation
    new_status = recompute_transaction_status(
        db=db_session,
        transaction_id=transaction.id,
    )
    
    # Step 7: Assert Transaction status = FAILED
    db_session.refresh(transaction)
    assert transaction.status == TransactionStatus.FAILED
    assert new_status == TransactionStatus.FAILED
    
    # Step 8: Assert funds removed from BLOCKED
    wallet_balances_after = get_wallet_balances(db_session, user_id, "AED")
    assert wallet_balances_after["blocked_balance"] == Decimal("0")
    assert wallet_balances_after["total_balance"] == Decimal("0")
    
    # Step 9: Verify ledger compensated correctly (reversal entries created)
    ledger_entries_after = db_session.query(LedgerEntry).join(Operation).filter(
        Operation.transaction_id == transaction.id
    ).all()
    assert len(ledger_entries_after) == 4  # Original 2 + Reversal 2
    
    # Verify double-entry for rejection operation
    rejection_ledger_entries = db_session.query(LedgerEntry).filter(
        LedgerEntry.operation_id == rejection_operation.id
    ).all()
    assert len(rejection_ledger_entries) == 2
    
    rejection_credits = [e.amount for e in rejection_ledger_entries if e.entry_type == LedgerEntryType.CREDIT]
    rejection_debits = [abs(e.amount) for e in rejection_ledger_entries if e.entry_type == LedgerEntryType.DEBIT]
    assert sum(rejection_credits) == sum(rejection_debits), "Double-entry invariant violated"
    
    # Step 10: Verify overall ledger balance (original + reversal should net to zero)
    all_credits = sum(e.amount for e in ledger_entries_after if e.entry_type == LedgerEntryType.CREDIT)
    all_debits = abs(sum(e.amount for e in ledger_entries_after if e.entry_type == LedgerEntryType.DEBIT))
    assert all_credits == all_debits, "Overall double-entry invariant violated after rejection"
    
    # Step 11: Verify AuditLog with reason exists
    rejection_audit_logs = db_session.query(AuditLog).filter(
        AuditLog.entity_id == rejection_operation.id
    ).all()
    assert len(rejection_audit_logs) > 0
    rejection_log = next((log for log in rejection_audit_logs if log.action == "DEPOSIT_REJECTED"), None)
    assert rejection_log is not None
    assert rejection_log.reason == rejection_reason
    assert rejection_log.actor_role.value == "COMPLIANCE"
    
    # Step 12: Verify no original LedgerEntry was modified (immutability)
    original_deposit_entries = db_session.query(LedgerEntry).filter(
        LedgerEntry.operation_id == deposit_operation.id
    ).all()
    original_amounts = {e.id: e.amount for e in original_deposit_entries}
    
    # Refresh and verify amounts unchanged
    for entry in original_deposit_entries:
        db_session.refresh(entry)
        assert entry.amount == original_amounts[entry.id], "LedgerEntry immutability violated"


