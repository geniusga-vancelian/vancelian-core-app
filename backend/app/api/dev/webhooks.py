"""
DEV-ONLY webhook utilities for local development and testing
"""

import hmac
import hashlib
import time
import json
from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.infrastructure.settings import get_settings

router = APIRouter(prefix="/webhooks/zand/deposit", tags=["dev-webhooks"])

settings = get_settings()


class SignWebhookRequest(BaseModel):
    """Request model for signing a webhook payload"""
    provider_event_id: str = Field(..., description="Unique event ID")
    iban: str = Field(..., description="IBAN identifier")
    user_sub: UUID = Field(..., description="User UUID (from JWT sub)")
    amount: str = Field(..., description="Deposit amount as string")
    currency: str = Field(default="AED", description="Currency code")
    occurred_at: Optional[str] = Field(None, description="ISO8601 timestamp (default: now)")


class SignWebhookResponse(BaseModel):
    """Response model with signed webhook payload and headers"""
    payload: dict = Field(..., description="Exact JSON payload to send")
    headers: dict = Field(..., description="Headers including signature and timestamp")
    curl_example: str = Field(..., description="Ready-to-run curl command")


def compute_hmac_signature(payload_bytes: bytes, secret: str) -> str:
    """
    Compute HMAC-SHA256 signature over raw payload bytes.
    
    This uses the SAME algorithm as production verification:
    - Signature is computed over EXACT raw body bytes (canonical representation)
    - Uses HMAC-SHA256 with the webhook secret
    
    Args:
        payload_bytes: Raw payload bytes (exact JSON string bytes)
        secret: Webhook secret key
    
    Returns:
        Hex-encoded HMAC signature
    """
    return hmac.new(
        secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()


@router.post("/sign", response_model=SignWebhookResponse, summary="Generate signed webhook request (DEV-ONLY)")
async def sign_webhook_request(request: SignWebhookRequest) -> SignWebhookResponse:
    """
    Generate a signed ZAND webhook request for testing.
    
    **DEV-ONLY**: This endpoint is only available when DEV_MODE=true.
    Returns 404 if DEV_MODE=false.
    
    This endpoint:
    1. Takes webhook payload fields
    2. Generates exact JSON payload
    3. Computes HMAC-SHA256 signature using the SAME secret and algorithm as production
    4. Generates timestamp header
    5. Returns payload + headers + curl example
    
    **Security**: Uses the same ZAND_WEBHOOK_SECRET as production verification.
    The signature is computed over EXACT raw JSON bytes (canonical representation).
    
    **Example Usage**:
    ```bash
    curl -X POST http://localhost:8000/dev/v1/webhooks/zand/deposit/sign \\
      -H "Content-Type: application/json" \\
      -d '{
        "provider_event_id": "test-123",
        "iban": "AE123456789012345678901",
        "user_sub": "11111111-1111-1111-1111-111111111111",
        "amount": "1000.00",
        "currency": "AED"
      }'
    ```
    """
    if not settings.DEV_MODE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Endpoint not available (DEV_MODE=false)"}}
        )
    
    if not settings.ZAND_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "CONFIGURATION_ERROR",
                    "message": "ZAND_WEBHOOK_SECRET not configured",
                    "details": {"hint": "Set ZAND_WEBHOOK_SECRET in environment variables"}
                }
            }
        )
    
    # Generate timestamp if not provided
    occurred_at_str = request.occurred_at
    if not occurred_at_str:
        occurred_at_str = datetime.utcnow().isoformat() + "Z"
    
    # Build exact payload (matching ZandDepositWebhookPayload schema)
    payload_dict = {
        "provider_event_id": request.provider_event_id,
        "iban": request.iban,
        "user_id": str(request.user_sub),  # Convert UUID to string
        "amount": request.amount,
        "currency": request.currency.upper(),
        "occurred_at": occurred_at_str,
    }
    
    # Generate exact JSON bytes (canonical representation)
    # This must match exactly what the webhook endpoint receives
    payload_json = json.dumps(payload_dict, separators=(',', ':'))  # Compact JSON (no spaces)
    payload_bytes = payload_json.encode('utf-8')
    
    # Compute signature over exact raw bytes (same as production)
    signature = compute_hmac_signature(payload_bytes, settings.ZAND_WEBHOOK_SECRET)
    
    # Generate timestamp header
    timestamp = str(int(time.time()))
    
    # Build headers
    headers = {
        "X-Zand-Signature": signature,
        "X-Zand-Timestamp": timestamp,
        "Content-Type": "application/json"
    }
    
    # Generate curl example
    curl_example = f"""curl -X POST http://localhost:8000/webhooks/v1/zand/deposit \\
  -H "Content-Type: application/json" \\
  -H "X-Zand-Signature: {signature}" \\
  -H "X-Zand-Timestamp: {timestamp}" \\
  -d '{payload_json}'"""
    
    return SignWebhookResponse(
        payload=payload_dict,
        headers=headers,
        curl_example=curl_example
    )

