"""
DEV-ONLY E2E helper endpoints for local testing
⚠️ These endpoints are ONLY available when DEV_MODE=true
"""

import json
import uuid
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from decimal import Decimal
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import httpx

from app.infrastructure.settings import get_settings
from app.infrastructure.database import get_db
from app.core.users.models import User, UserStatus
from app.core.accounts.models import AccountType
from app.core.transactions.models import Transaction
from app.services.wallet_helpers import ensure_wallet_accounts, get_wallet_balances
from app.utils.trace_id import trace_id_context
import jwt

router = APIRouter(prefix="/e2e", tags=["dev-e2e"])
settings = get_settings()


class E2EDepositFlowRequest(BaseModel):
    """Request for E2E deposit flow"""
    email: Optional[str] = Field(default="user@vancelian.dev", description="User email")
    sub: Optional[str] = Field(default="11111111-1111-1111-1111-111111111111", description="User subject (external_subject)")
    currency: Optional[str] = Field(default="AED", description="Currency code")
    amount: Optional[str] = Field(default="1000.00", description="Deposit amount")
    provider_event_id: Optional[str] = Field(default=None, description="Provider event ID (auto-generated if not provided)")
    iban: Optional[str] = Field(default="AE123456789012345678901", description="IBAN identifier")


class E2EDepositFlowResponse(BaseModel):
    """Response for E2E deposit flow"""
    user_id: str
    subject: str
    email: str
    token: str
    provider_event_id: str
    webhook_submit_status: str  # "success", "duplicate", "error"
    webhook_error: Optional[dict] = None
    wallet_balances: dict[str, str]  # available, blocked, locked, total
    last_transaction: Optional[dict] = None  # id, status, created_at


def generate_user_token(subject: str, email: str) -> str:
    """Generate USER JWT token"""
    if not settings.JWT_SECRET:
        raise ValueError("JWT_SECRET not configured")
    
    now = datetime.now(timezone.utc)
    exp = int((now + timedelta(days=7)).timestamp())
    
    payload = {
        "sub": subject,
        "email": email,
        "roles": ["USER"],
        "exp": exp,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
    }
    
    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def compute_hmac_signature(payload_bytes: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature"""
    import hmac
    import hashlib
    return hmac.new(
        secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()


@router.post(
    "/deposit-flow",
    response_model=E2EDepositFlowResponse,
    summary="E2E deposit flow helper (DEV-ONLY)",
    description="""
    **DEV-ONLY**: Complete E2E deposit flow in one call.
    
    This endpoint:
    1. Bootstraps user (creates or gets existing)
    2. Generates USER token
    3. Generates signed deposit webhook request
    4. Submits webhook internally
    5. Returns wallet balances + transaction status
    
    **Idempotent**: If provider_event_id already exists, returns existing transaction status.
    
    ⚠️ Never expose this endpoint in production!
    """,
)
async def e2e_deposit_flow(
    request: E2EDepositFlowRequest = E2EDepositFlowRequest(),
    db: Session = Depends(get_db),
) -> E2EDepositFlowResponse:
    """
    Complete E2E deposit flow: bootstrap user + token + webhook + balances.
    """
    # Security check
    if not settings.DEV_MODE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Endpoint not found",
                    "trace_id": trace_id_context.get(),
                }
            },
        )
    
    # 1. Bootstrap user
    email = request.email or "user@vancelian.dev"
    external_subject = request.sub or "11111111-1111-1111-1111-111111111111"
    currency = request.currency or "AED"
    
    # Find or create user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = db.query(User).filter(User.external_subject == external_subject).first()
    if not user:
        user = User(
            email=email,
            status=UserStatus.ACTIVE,
            external_subject=external_subject,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Ensure wallet accounts exist
    ensure_wallet_accounts(db, user.id, currency)
    db.commit()
    
    # 2. Generate USER token
    # Use user.id (UUID) as subject for token
    user_subject = str(user.id)
    token = generate_user_token(user_subject, user.email)
    
    # 3. Generate signed webhook request
    if not settings.ZAND_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "CONFIG_ERROR",
                    "message": "ZAND_WEBHOOK_SECRET not configured",
                    "trace_id": trace_id_context.get(),
                }
            },
        )
    
    provider_event_id = request.provider_event_id or f"e2e-{uuid.uuid4()}"
    amount = request.amount or "1000.00"
    iban = request.iban or "AE123456789012345678901"
    
    # Build payload
    occurred_at_str = datetime.utcnow().isoformat() + "Z"
    payload_dict = {
        "provider_event_id": provider_event_id,
        "iban": iban,
        "user_id": str(user.id),
        "amount": amount,
        "currency": currency.upper(),
        "occurred_at": occurred_at_str,
    }
    
    # Generate exact JSON bytes
    payload_json = json.dumps(payload_dict, separators=(',', ':'))
    payload_bytes = payload_json.encode('utf-8')
    
    # Compute signature
    signature = compute_hmac_signature(payload_bytes, settings.ZAND_WEBHOOK_SECRET)
    timestamp = str(int(time.time()))
    
    # 4. Submit webhook internally (using httpx)
    webhook_status = "success"
    webhook_error = None
    transaction_id = None
    
    try:
        # Call webhook endpoint internally
        # Use localhost since we're in the same container/network
        webhook_url = "http://localhost:8000/webhooks/v1/zand/deposit"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                webhook_url,
                content=payload_bytes,
                headers={
                    "X-Zand-Signature": signature,
                    "X-Zand-Timestamp": timestamp,
                    "Content-Type": "application/json",
                },
            )
            
            if response.status_code == 200:
                webhook_data = response.json()
                transaction_id = webhook_data.get("transaction_id")
            elif response.status_code == 409:
                # Duplicate - check existing transaction
                webhook_status = "duplicate"
                # Find existing transaction by provider_event_id
                existing_tx = db.query(Transaction).filter(
                    Transaction.external_reference == provider_event_id
                ).first()
                if existing_tx:
                    transaction_id = str(existing_tx.id)
            else:
                webhook_status = "error"
                try:
                    error_data = response.json()
                    webhook_error = error_data.get("error", {})
                except:
                    webhook_error = {
                        "code": f"HTTP_{response.status_code}",
                        "message": response.text[:200],
                    }
    except Exception as e:
        webhook_status = "error"
        webhook_error = {
            "code": "WEBHOOK_SUBMIT_ERROR",
            "message": str(e),
        }
    
    # 5. Get wallet balances
    balances = get_wallet_balances(db, user.id, currency)
    wallet_balances = {
        "available": str(balances.get("available_balance", Decimal("0"))),
        "blocked": str(balances.get("blocked_balance", Decimal("0"))),
        "locked": str(balances.get("locked_balance", Decimal("0"))),
        "total": str(balances.get("total_balance", Decimal("0"))),
    }
    
    # 6. Get last transaction
    last_transaction = None
    if transaction_id:
        tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if tx:
            last_transaction = {
                "id": str(tx.id),
                "status": tx.status.value if hasattr(tx.status, 'value') else str(tx.status),
                "created_at": tx.created_at.isoformat() if hasattr(tx, 'created_at') and tx.created_at else None,
            }
    else:
        # Try to find transaction by provider_event_id
        tx = db.query(Transaction).filter(Transaction.external_reference == provider_event_id).first()
        if tx:
            last_transaction = {
                "id": str(tx.id),
                "status": tx.status.value if hasattr(tx.status, 'value') else str(tx.status),
                "created_at": tx.created_at.isoformat() if hasattr(tx, 'created_at') and tx.created_at else None,
            }
    
    return E2EDepositFlowResponse(
        user_id=str(user.id),
        subject=user_subject,  # User ID used as subject
        email=user.email,
        token=token,
        provider_event_id=provider_event_id,
        webhook_submit_status=webhook_status,
        webhook_error=webhook_error,
        wallet_balances=wallet_balances,
        last_transaction=last_transaction,
    )

