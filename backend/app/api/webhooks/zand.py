"""
ZAND Bank webhook endpoints
"""

import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.infrastructure.database import get_db
from app.infrastructure.logging_config import trace_id_context
from app.core.transactions.models import Transaction, TransactionType, TransactionStatus
from app.core.ledger.models import Operation
from app.core.compliance.models import AuditLog
from app.core.security.models import Role
from app.schemas.webhooks import ZandDepositWebhookPayload, ZandDepositWebhookResponse
from app.services.fund_services import record_deposit_blocked
from app.utils.webhook_security import verify_zand_webhook_security
from app.utils.metrics import record_webhook_received, record_webhook_rejected

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/zand/deposit",
    response_model=ZandDepositWebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="ZAND Bank deposit webhook",
    description="Receive AED deposit notifications from ZAND Bank. INTERNAL / BANK ONLY endpoint. Requires HMAC signature verification.",
)
async def zand_deposit_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_zand_signature: str = Header(..., alias="X-Zand-Signature", description="HMAC-SHA256 signature of request body"),
    x_zand_timestamp: str = Header(None, alias="X-Zand-Timestamp", description="Unix timestamp for replay protection"),
) -> ZandDepositWebhookResponse:
    """
    Process ZAND Bank deposit webhook with HMAC signature verification.
    
    Security Requirements:
    1. HMAC-SHA256 signature verification (MANDATORY)
    2. Timestamp/replay protection (if timestamp provided)
    3. Strict idempotency via provider_event_id
    
    This endpoint:
    1. Reads raw request body
    2. Verifies HMAC signature
    3. Validates timestamp (if provided)
    4. Validates payload schema
    5. Checks idempotency (provider_event_id + transaction_id)
    6. Creates Transaction if not exists (idempotent)
    7. Calls record_deposit_blocked() to record deposit in ledger
    8. Transaction Status Engine updates status to COMPLIANCE_REVIEW
    9. Creates AuditLog entry
    
    Idempotence:
    - provider_event_id must be unique per transaction
    - Duplicate requests return 409 Conflict
    - Existing transactions are returned with 200 OK (already processed)
    
    Security:
    - Signature verification required (rejects on failure with 401)
    - Timestamp tolerance: 300 seconds (5 minutes) by default
    - No funds released to AVAILABLE (compliance review required)
    """
    # Get trace_id for logging
    trace_id = trace_id_context.get("unknown")
    
    # Read raw request body for signature verification
    try:
        body_bytes = await request.body()
    except Exception as e:
        logger.error(f"Error reading request body: trace_id={trace_id}, error={str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Failed to read request body",
                    "details": {"trace_id": trace_id},
                    "trace_id": trace_id,
                }
            }
        )
    
    # Verify webhook signature and timestamp
    is_valid, error_message = verify_zand_webhook_security(
        payload_body=body_bytes,
        signature_header=x_zand_signature,
        timestamp_header=x_zand_timestamp,
    )
    
    if not is_valid:
        logger.error(
            f"Webhook security verification failed: trace_id={trace_id}, "
            f"reason={error_message}, signature_header={x_zand_signature[:16] if x_zand_signature else None}..."
        )
        
        # Record metrics
        reason = error_message or "signature_invalid"
        record_webhook_rejected(reason=reason)
        
        # Log security event
        from app.utils.security_logging import log_security_event
        log_security_event(
            action="WEBHOOK_SIGNATURE_FAILED",
            details={
                "webhook_provider": "ZAND",
                "reason": error_message,
                "path": request.url.path,
            },
            trace_id=trace_id,
            db=db,
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_SIGNATURE",
                    "message": error_message or "Webhook signature verification failed",
                    "details": {"trace_id": trace_id},
                    "trace_id": trace_id,
                }
            }
        )
    
    # Parse payload (after security verification)
    try:
        import json
        payload_dict = json.loads(body_bytes.decode('utf-8'))
        payload = ZandDepositWebhookPayload(**payload_dict)
    except Exception as e:
        logger.error(
            f"Invalid webhook payload: trace_id={trace_id}, error={str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid payload format",
                    "details": {"trace_id": trace_id, "error": str(e)},
                    "trace_id": trace_id,
                }
            }
        )
    
    # Validate provider_event_id is present (mandatory for idempotency)
    if not payload.provider_event_id:
        logger.error(f"Missing provider_event_id: trace_id={trace_id}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "provider_event_id is required for idempotency",
                    "details": {"trace_id": trace_id},
                    "trace_id": trace_id,
                }
            }
        )
    
    # Record webhook received metric
    record_webhook_received()
    
    logger.info(
        f"ZAND webhook received: trace_id={trace_id}, provider_event_id={payload.provider_event_id}, "
        f"amount={payload.amount} {payload.currency}, user_id={payload.user_id}, "
        f"signature_verified=True"
    )
    
    # Check for existing Transaction (idempotence via external_reference)
    existing_transaction = db.query(Transaction).filter(
        Transaction.external_reference == payload.provider_event_id
    ).first()
    
    if existing_transaction:
        logger.info(
            f"Duplicate webhook detected (already processed): trace_id={trace_id}, "
            f"provider_event_id={payload.provider_event_id}, "
            f"transaction_id={existing_transaction.id}"
        )
        # Record duplicate metric (idempotent - not a rejection)
        # Webhook was already received and processed, so we don't record as rejected
        # Return existing transaction (idempotent response)
        return ZandDepositWebhookResponse(
            status="accepted",
            transaction_id=str(existing_transaction.id),
        )
    
    # Create Transaction
    transaction = Transaction(
        user_id=payload.user_id,
        type=TransactionType.DEPOSIT,
        status=TransactionStatus.INITIATED,  # Will be updated to COMPLIANCE_REVIEW by Transaction Status Engine
        external_reference=payload.provider_event_id,
        metadata={
            "iban": payload.iban,
            "occurred_at": payload.occurred_at.isoformat(),
            "provider": "ZAND",
            "trace_id": trace_id,
        },
    )
    db.add(transaction)
    db.flush()  # Get transaction.id
    
    try:
        # Record deposit as BLOCKED (compliance review required)
        # idempotency_key ensures Operation uniqueness
        operation = record_deposit_blocked(
            db=db,
            user_id=payload.user_id,
            currency=payload.currency,
            amount=payload.amount,
            transaction_id=transaction.id,
            idempotency_key=payload.provider_event_id,  # Unique per provider_event_id
            provider_reference=payload.provider_event_id,
        )
        
        # Transaction Status Engine will automatically update status to COMPLIANCE_REVIEW
        # after record_deposit_blocked completes (via recompute_transaction_status)
        
        # Create AuditLog
        audit_log = AuditLog(
            actor_user_id=None,  # System operation
            actor_role=Role.OPS,
            action="ZAND_DEPOSIT_RECEIVED",
            entity_type="Transaction",
            entity_id=transaction.id,
            before=None,
            after={
                "transaction_id": str(transaction.id),
                "provider_event_id": payload.provider_event_id,
                "user_id": str(payload.user_id),
                "amount": str(payload.amount),
                "currency": payload.currency,
                "iban": payload.iban,
                "trace_id": trace_id,
            },
            reason=None,
        )
        db.add(audit_log)
        db.commit()
        
        logger.info(
            f"ZAND deposit processed successfully: trace_id={trace_id}, "
            f"transaction_id={transaction.id}, operation_id={operation.id}, "
            f"provider_event_id={payload.provider_event_id}"
        )
        
        return ZandDepositWebhookResponse(
            status="accepted",
            transaction_id=str(transaction.id),
        )
        
    except IntegrityError as e:
        db.rollback()
        # Handle duplicate idempotency_key (Operation already exists)
        logger.warning(
            f"Duplicate operation detected (idempotency): trace_id={trace_id}, "
            f"provider_event_id={payload.provider_event_id}, error={str(e)}"
        )
        # Check if transaction was created but operation failed
        existing_op = db.query(Operation).filter(
            Operation.idempotency_key == payload.provider_event_id
        ).first()
        
        if existing_op and existing_op.transaction_id:
            existing_tx = db.query(Transaction).filter(
                Transaction.id == existing_op.transaction_id
            ).first()
            if existing_tx:
                return ZandDepositWebhookResponse(
                    status="accepted",
                    transaction_id=str(existing_tx.id),
                )
        
        # Record duplicate rejection
        record_webhook_rejected(reason="duplicate")
        
        # If we can't find existing transaction, return conflict
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "DUPLICATE_EVENT",
                    "message": f"Duplicate webhook event: {payload.provider_event_id}",
                    "details": {"trace_id": trace_id, "provider_event_id": payload.provider_event_id},
                    "trace_id": trace_id,
                }
            }
        )
    except Exception as e:
        db.rollback()
        logger.error(
            f"Error processing ZAND deposit webhook: trace_id={trace_id}, "
            f"provider_event_id={payload.provider_event_id}, error={str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Error processing deposit",
                    "details": {"trace_id": trace_id},
                    "trace_id": trace_id,
                }
            }
        )
