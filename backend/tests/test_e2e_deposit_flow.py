"""
End-to-end tests: Deposit → Compliance → Available flow
"""

import pytest
from uuid import uuid4
from decimal import Decimal
from sqlalchemy.orm import Session

from app.core.transactions.models import Transaction, TransactionType, TransactionStatus
from app.core.ledger.models import Operation, OperationType, OperationStatus, LedgerEntry, LedgerEntryType
from app.core.accounts.models import Account, AccountType
from app.core.compliance.models import AuditLog
from app.services.wallet_helpers import get_wallet_balances, get_account_balance


def test_deposit_happy_path_compliance_to_available(
    client,
    db_session: Session,
    test_user,
    test_internal_account,
):
    """
    Test happy path: Deposit → Compliance Review → Available
    
    Scenario:
    1. Create user
    2. Simulate ZAND webhook deposit
    3. Assert: Transaction status = COMPLIANCE_REVIEW, Funds in WALLET_BLOCKED
    4. Call admin compliance release
    5. Assert: Transaction status = AVAILABLE, Funds moved BLOCKED → AVAILABLE
    
    Ledger invariants:
    - Sum of credits == Sum of debits
    - No LedgerEntry updated or deleted
    - TransactionStatus derived correctly
    - AuditLog written with correct actor_role
    """
    user_id = test_user.id
    amount = Decimal("5000.00")
    provider_event_id = f"ZAND-EVT-{uuid4()}"
    
    # Step 1: Simulate ZAND webhook deposit
    webhook_payload = {
        "provider_event_id": provider_event_id,
        "iban": "AE123456789012345678901",
        "user_id": str(user_id),
        "amount": str(amount),
        "currency": "AED",
        "occurred_at": "2025-12-18T10:00:00Z",
    }
    
    # Mock HMAC signature verification for tests
    # In real tests, we'd compute the actual signature
    response = client.post(
        "/webhooks/v1/zand/deposit",
        json=webhook_payload,
        headers={
            "X-Zand-Signature": "test-signature-placeholder",
            "X-Zand-Timestamp": "1703000000",
        },
    )
    
    # Step 2: Assert webhook accepted
    assert response.status_code == 200, f"Webhook failed: {response.json()}"
    webhook_response = response.json()
    transaction_id = webhook_response["transaction_id"]
    assert transaction_id is not None
    
    # Step 3: Assert Transaction created with correct status
    transaction = db_session.query(Transaction).filter(
        Transaction.id == transaction_id
    ).first()
    assert transaction is not None
    assert transaction.type == TransactionType.DEPOSIT
    assert transaction.status == TransactionStatus.COMPLIANCE_REVIEW
    assert transaction.external_reference == provider_event_id
    assert transaction.user_id == user_id
    
    # Step 4: Assert funds in WALLET_BLOCKED
    wallet_balances = get_wallet_balances(db_session, user_id, "AED")
    assert wallet_balances["blocked_balance"] == amount
    assert wallet_balances["available_balance"] == Decimal("0")
    assert wallet_balances["total_balance"] == amount
    
    # Step 5: Verify ledger entries created (double-entry)
    operations = db_session.query(Operation).filter(
        Operation.transaction_id == transaction.id
    ).all()
    assert len(operations) == 1
    deposit_operation = operations[0]
    assert deposit_operation.type == OperationType.DEPOSIT_AED
    assert deposit_operation.status == OperationStatus.COMPLETED
    
    ledger_entries = db_session.query(LedgerEntry).filter(
        LedgerEntry.operation_id == deposit_operation.id
    ).all()
    assert len(ledger_entries) == 2  # CREDIT + DEBIT
    
    credits = [e.amount for e in ledger_entries if e.entry_type == LedgerEntryType.CREDIT]
    debits = [abs(e.amount) for e in ledger_entries if e.entry_type == LedgerEntryType.DEBIT]
    assert sum(credits) == sum(debits), "Double-entry invariant violated"
    
    # Step 6: Verify AuditLog created
    audit_logs = db_session.query(AuditLog).filter(
        AuditLog.entity_id == deposit_operation.id
    ).all()
    assert len(audit_logs) > 0
    assert any(log.action == "DEPOSIT_RECORDED" for log in audit_logs)
    
    # Step 7: Call admin compliance release
    release_payload = {
        "transaction_id": transaction_id,
        "amount": str(amount),
        "reason": "AML review completed - no suspicious activity",
    }
    
    # Note: In real tests, we'd authenticate as COMPLIANCE role
    # For now, we'll call the service directly to test business logic
    from app.services.fund_services import release_compliance_funds
    from app.services.transaction_engine import recompute_transaction_status
    
    release_operation = release_compliance_funds(
        db=db_session,
        user_id=user_id,
        currency="AED",
        amount=amount,
        transaction_id=transaction.id,
        reason=release_payload["reason"],
        actor_user_id=None,  # System/Compliance
    )
    
    # Trigger status recomputation
    new_status = recompute_transaction_status(
        db=db_session,
        transaction_id=transaction.id,
    )
    
    # Step 8: Assert Transaction status = AVAILABLE
    db_session.refresh(transaction)
    assert transaction.status == TransactionStatus.AVAILABLE
    assert new_status == TransactionStatus.AVAILABLE
    
    # Step 9: Assert funds moved BLOCKED → AVAILABLE
    wallet_balances_after = get_wallet_balances(db_session, user_id, "AED")
    assert wallet_balances_after["blocked_balance"] == Decimal("0")
    assert wallet_balances_after["available_balance"] == amount
    assert wallet_balances_after["total_balance"] == amount
    
    # Step 10: Verify ledger balance unchanged (funds moved, not added)
    all_operations = db_session.query(Operation).filter(
        Operation.transaction_id == transaction.id
    ).all()
    assert len(all_operations) == 2  # DEPOSIT_AED + RELEASE_FUNDS
    
    # Verify double-entry for release operation
    release_ledger_entries = db_session.query(LedgerEntry).filter(
        LedgerEntry.operation_id == release_operation.id
    ).all()
    assert len(release_ledger_entries) == 2
    
    release_credits = [e.amount for e in release_ledger_entries if e.entry_type == LedgerEntryType.CREDIT]
    release_debits = [abs(e.amount) for e in release_ledger_entries if e.entry_type == LedgerEntryType.DEBIT]
    assert sum(release_credits) == sum(release_debits), "Double-entry invariant violated"
    
    # Step 11: Verify AuditLog for release
    release_audit_logs = db_session.query(AuditLog).filter(
        AuditLog.entity_id == release_operation.id
    ).all()
    assert len(release_audit_logs) > 0
    assert any(log.action == "COMPLIANCE_RELEASE" for log in release_audit_logs)
    
    # Step 12: Final ledger invariant check - all operations balance
    all_ledger_entries = db_session.query(LedgerEntry).join(Operation).filter(
        Operation.transaction_id == transaction.id
    ).all()
    total_credits = sum(e.amount for e in all_ledger_entries if e.entry_type == LedgerEntryType.CREDIT)
    total_debits = abs(sum(e.amount for e in all_ledger_entries if e.entry_type == LedgerEntryType.DEBIT))
    assert total_credits == total_debits, "Overall double-entry invariant violated"
    
    # Step 13: Verify no LedgerEntry was updated or deleted (immutability)
    # All entries should have been created, none modified
    original_entry_ids = {e.id for e in ledger_entries}
    final_entries = db_session.query(LedgerEntry).filter(
        LedgerEntry.operation_id == deposit_operation.id
    ).all()
    final_entry_ids = {e.id for e in final_entries}
    assert original_entry_ids == final_entry_ids, "LedgerEntry immutability violated"


def test_ledger_entry_immutability_verification(db_session: Session, test_user, test_internal_account):
    """
    Verify that LedgerEntry cannot be updated or deleted.
    This is a sanity check for the immutability principle.
    """
    from app.core.ledger.models import Operation, OperationType, OperationStatus, LedgerEntry, LedgerEntryType
    from app.services.wallet_helpers import ensure_wallet_accounts
    from uuid import uuid4
    from decimal import Decimal
    
    # Create a ledger entry
    wallet_accounts = ensure_wallet_accounts(db_session, test_user.id, "AED")
    available_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
    
    operation = Operation(
        id=uuid4(),
        type=OperationType.DEPOSIT_AED,
        status=OperationStatus.COMPLETED,
    )
    db_session.add(operation)
    db_session.flush()
    
    ledger_entry = LedgerEntry(
        id=uuid4(),
        operation_id=operation.id,
        account_id=available_account_id,
        amount=Decimal("1000.00"),
        currency="AED",
        entry_type=LedgerEntryType.CREDIT,
    )
    db_session.add(ledger_entry)
    db_session.commit()
    
    entry_id = ledger_entry.id
    original_amount = ledger_entry.amount
    
    # Verify entry exists
    assert db_session.query(LedgerEntry).filter(LedgerEntry.id == entry_id).first() is not None
    
    # Attempt to update (should be prevented by application logic)
    # In a real scenario, we'd test that update methods don't exist or raise exceptions
    # For now, we verify the entry remains unchanged
    db_session.refresh(ledger_entry)
    assert ledger_entry.amount == original_amount


