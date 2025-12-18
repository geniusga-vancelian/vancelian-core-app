"""
Integration tests for ZAND webhook deposit endpoint
"""

import pytest
from uuid import uuid4, UUID
from decimal import Decimal
from sqlalchemy.orm import Session
import hmac
import hashlib
import json
import time

from app.core.transactions.models import Transaction, TransactionType, TransactionStatus
from app.core.ledger.models import Operation, OperationType, OperationStatus, LedgerEntry, LedgerEntryType
from app.core.accounts.models import Account, AccountType
from app.services.wallet_helpers import get_wallet_balances
from app.infrastructure.settings import get_settings


def compute_hmac_signature(payload_bytes: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature"""
    return hmac.new(
        secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()


def test_zand_deposit_webhook_with_valid_signature(
    client,
    db_session: Session,
    test_user,
    test_internal_account,
):
    """
    Test ZAND deposit webhook with valid HMAC signature.
    
    Flow:
    1. Bootstrap user (test_user fixture)
    2. Generate signed webhook payload using backend secret
    3. POST /webhooks/v1/zand/deposit
    4. Assert 200/201 response
    5. Assert transaction created with status COMPLIANCE_REVIEW
    6. Assert funds in BLOCKED account
    7. Assert ledger entries created (double-entry)
    """
    settings = get_settings()
    if not settings.ZAND_WEBHOOK_SECRET:
        pytest.skip("ZAND_WEBHOOK_SECRET not configured")
    
    user_id = test_user.id
    amount = Decimal("1000.00")
    provider_event_id = f"TEST-EVT-{uuid4()}"
    
    # Build payload
    payload_dict = {
        "provider_event_id": provider_event_id,
        "iban": "AE123456789012345678901",
        "user_id": str(user_id),
        "amount": str(amount),
        "currency": "AED",
        "occurred_at": "2025-12-18T10:00:00Z",
    }
    
    # Generate exact JSON bytes (canonical)
    payload_json = json.dumps(payload_dict, separators=(',', ':'))
    payload_bytes = payload_json.encode('utf-8')
    
    # Compute signature using same secret as backend
    signature = compute_hmac_signature(payload_bytes, settings.ZAND_WEBHOOK_SECRET)
    
    # Generate timestamp
    timestamp = str(int(time.time()))
    
    # POST webhook
    response = client.post(
        "/webhooks/v1/zand/deposit",
        content=payload_bytes,
        headers={
            "X-Zand-Signature": signature,
            "X-Zand-Timestamp": timestamp,
            "Content-Type": "application/json",
        },
    )
    
    # Assert 200 OK
    assert response.status_code == 200, f"Webhook failed: {response.json()}"
    
    webhook_response = response.json()
    assert "transaction_id" in webhook_response
    assert webhook_response.get("status") == "accepted"
    
    transaction_id_str = webhook_response["transaction_id"]
    transaction_id = UUID(transaction_id_str)
    
    # Assert Transaction created
    transaction = db_session.query(Transaction).filter(
        Transaction.id == transaction_id
    ).first()
    assert transaction is not None
    assert transaction.type == TransactionType.DEPOSIT
    assert transaction.status == TransactionStatus.COMPLIANCE_REVIEW
    assert transaction.external_reference == provider_event_id
    assert transaction.user_id == user_id
    
    # Assert funds in WALLET_BLOCKED
    wallet_balances = get_wallet_balances(db_session, user_id, "AED")
    assert wallet_balances["blocked_balance"] == amount
    assert wallet_balances["available_balance"] == Decimal("0")
    assert wallet_balances["total_balance"] == amount
    
    # Assert ledger entries created (double-entry)
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
    assert sum(credits) == amount


def test_zand_deposit_webhook_idempotency(
    client,
    db_session: Session,
    test_user,
    test_internal_account,
):
    """
    Test webhook idempotency: duplicate provider_event_id returns existing transaction.
    """
    settings = get_settings()
    if not settings.ZAND_WEBHOOK_SECRET:
        pytest.skip("ZAND_WEBHOOK_SECRET not configured")
    
    user_id = test_user.id
    amount = Decimal("500.00")
    provider_event_id = f"IDEMPOTENT-{uuid4()}"
    
    # Build payload
    payload_dict = {
        "provider_event_id": provider_event_id,
        "iban": "AE123456789012345678901",
        "user_id": str(user_id),
        "amount": str(amount),
        "currency": "AED",
        "occurred_at": "2025-12-18T10:00:00Z",
    }
    
    payload_json = json.dumps(payload_dict, separators=(',', ':'))
    payload_bytes = payload_json.encode('utf-8')
    signature = compute_hmac_signature(payload_bytes, settings.ZAND_WEBHOOK_SECRET)
    
    import time
    timestamp = str(int(time.time()))
    
    # First request
    response1 = client.post(
        "/webhooks/v1/zand/deposit",
        content=payload_bytes,
        headers={
            "X-Zand-Signature": signature,
            "X-Zand-Timestamp": timestamp,
            "Content-Type": "application/json",
        },
    )
    assert response1.status_code == 200
    transaction_id_1 = response1.json()["transaction_id"]
    
    # Second request (duplicate)
    timestamp2 = str(int(time.time()))  # New timestamp but same payload
    # Recompute signature for same payload (should be same)
    signature2 = compute_hmac_signature(payload_bytes, settings.ZAND_WEBHOOK_SECRET)
    
    response2 = client.post(
        "/webhooks/v1/zand/deposit",
        content=payload_bytes,
        headers={
            "X-Zand-Signature": signature2,
            "X-Zand-Timestamp": timestamp2,
            "Content-Type": "application/json",
        },
    )
    
    # Should return 200 with same transaction_id (idempotent)
    assert response2.status_code == 200
    transaction_id_2 = response2.json()["transaction_id"]
    assert transaction_id_1 == transaction_id_2, "Duplicate webhook should return same transaction_id"


def test_zand_deposit_webhook_invalid_signature(
    client,
    db_session: Session,
    test_user,
):
    """
    Test webhook with invalid signature returns 401.
    """
    user_id = test_user.id
    payload_dict = {
        "provider_event_id": f"INVALID-SIG-{uuid4()}",
        "iban": "AE123456789012345678901",
        "user_id": str(user_id),
        "amount": "1000.00",
        "currency": "AED",
        "occurred_at": "2025-12-18T10:00:00Z",
    }
    
    payload_json = json.dumps(payload_dict, separators=(',', ':'))
    payload_bytes = payload_json.encode('utf-8')
    
    # Use wrong signature
    invalid_signature = "invalid_signature_hex"
    
    response = client.post(
        "/webhooks/v1/zand/deposit",
        content=payload_bytes,
        headers={
            "X-Zand-Signature": invalid_signature,
            "X-Zand-Timestamp": str(int(time.time())),
            "Content-Type": "application/json",
        },
    )
    
    assert response.status_code == 401
    error_data = response.json()
    assert "error" in error_data
    assert error_data["error"]["code"] == "WEBHOOK_INVALID_SIGNATURE"

