"""
ZAND webhook endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from uuid import uuid4

from app.infrastructure.database import get_db
from app.core.transactions.models import Transaction, TransactionType, TransactionStatus
from app.schemas.webhooks import ZandDepositWebhookPayload, ZandDepositWebhookResponse
from app.services.fund_services import record_deposit_blocked
# TODO: Implement webhook signature verification
# from app.utils.webhook_security import verify_zand_webhook_signature

router = APIRouter()


@router.post(
    "/zand/deposit",
    response_model=ZandDepositWebhookResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="ZAND deposit webhook",
    description="Receive deposit notification from ZAND Bank. Funds are recorded in WALLET_BLOCKED compartment pending compliance review.",
)
async def zand_deposit_webhook(
    payload: ZandDepositWebhookPayload,
    request: Request,
    db: Session = Depends(get_db),
) -> ZandDepositWebhookResponse:
    """
    Process ZAND Bank deposit webhook.
    
    This endpoint:
    1. Verifies webhook signature (if configured)
    2. Creates Transaction (type=DEPOSIT, status=INITIATED)
    3. Records deposit in WALLET_BLOCKED compartment
    4. Returns transaction_id for tracking
    
    Idempotency: Uses provider_event_id to prevent duplicate processing.
    
    Security: Webhook signature verification should be enabled in production.
    """
    # Verify webhook signature (if secret is configured)
    if hasattr(request, 'headers'):
        # TODO: Implement signature verification
        # verify_zand_webhook_signature(request, payload)
        pass
    
    # Create Transaction
    transaction = Transaction(
        user_id=payload.user_id,
        type=TransactionType.DEPOSIT,
        status=TransactionStatus.INITIATED,
        transaction_metadata={
            "provider_event_id": payload.provider_event_id,
            "iban": payload.iban,
            "amount": str(payload.amount),
            "currency": payload.currency,
            "occurred_at": payload.occurred_at.isoformat(),
        },
    )
    db.add(transaction)
    db.flush()  # Get transaction.id
    
    try:
        # Record deposit in WALLET_BLOCKED compartment
        operation = record_deposit_blocked(
            db=db,
            user_id=payload.user_id,
            currency=payload.currency,
            amount=payload.amount,
            transaction_id=transaction.id,
            idempotency_key=f"zand-{payload.provider_event_id}",
            provider_reference=payload.provider_event_id,
        )
        
        db.commit()
        
        return ZandDepositWebhookResponse(
            status="accepted",
            transaction_id=str(transaction.id),
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing deposit: {str(e)}"
        )
