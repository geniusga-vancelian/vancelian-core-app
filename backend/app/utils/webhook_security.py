"""
Webhook security utilities - HMAC signature verification and replay protection
"""

import hmac
import hashlib
import time
import logging
from typing import Optional, Tuple
from fastapi import HTTPException, status

from app.infrastructure.settings import get_settings

logger = logging.getLogger(__name__)


class WebhookSecurityError(Exception):
    """Raised when webhook security verification fails"""
    pass


def verify_hmac_signature(
    payload_body: bytes,
    signature_header: str,
    secret: str,
) -> bool:
    """
    Verify HMAC-SHA256 signature using constant-time comparison.
    
    Args:
        payload_body: Raw request body (bytes)
        signature_header: Signature from X-Zand-Signature header
        secret: Shared secret key
    
    Returns:
        True if signature is valid, False otherwise
    
    Raises:
        WebhookSecurityError: If signature verification fails
    """
    if not secret:
        raise WebhookSecurityError("ZAND_WEBHOOK_SECRET not configured")
    
    if not signature_header:
        raise WebhookSecurityError("Signature header missing")
    
    # Compute expected signature
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(expected_signature, signature_header):
        logger.warning(
            f"HMAC signature verification failed: expected={expected_signature[:8]}..., "
            f"received={signature_header[:8]}..."
        )
        return False
    
    return True


def verify_timestamp(
    timestamp_header: Optional[str],
    tolerance_seconds: int,
) -> bool:
    """
    Verify timestamp to prevent replay attacks.
    
    Args:
        timestamp_header: Timestamp from X-Zand-Timestamp header (Unix timestamp as string)
        tolerance_seconds: Maximum allowed time difference in seconds
    
    Returns:
        True if timestamp is within tolerance, False otherwise
    
    Raises:
        WebhookSecurityError: If timestamp verification fails
    """
    if not timestamp_header:
        # If no timestamp provided, rely on strict idempotency only
        logger.debug("No timestamp header provided - relying on idempotency protection")
        return True
    
    try:
        timestamp = int(timestamp_header)
    except (ValueError, TypeError):
        raise WebhookSecurityError(f"Invalid timestamp format: {timestamp_header}")
    
    current_time = int(time.time())
    time_delta = abs(current_time - timestamp)
    
    if time_delta > tolerance_seconds:
        logger.warning(
            f"Timestamp verification failed: delta={time_delta}s, "
            f"tolerance={tolerance_seconds}s, timestamp={timestamp}, current={current_time}"
        )
        return False
    
    return True


def verify_zand_webhook_security(
    payload_body: bytes,
    signature_header: Optional[str],
    timestamp_header: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Complete webhook security verification for ZAND Bank webhooks.
    
    Performs:
    1. HMAC-SHA256 signature verification
    2. Timestamp/replay protection (if timestamp provided)
    
    Args:
        payload_body: Raw request body (bytes)
        signature_header: Signature from X-Zand-Signature header
        timestamp_header: Optional timestamp from X-Zand-Timestamp header
    
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if all checks pass
        - error_message: Error description if verification fails (None if valid)
    """
    settings = get_settings()
    
    # Check signature header is present
    if not signature_header:
        return False, "X-Zand-Signature header missing"
    
    # Verify HMAC signature
    try:
        if not verify_hmac_signature(
            payload_body=payload_body,
            signature_header=signature_header,
            secret=settings.ZAND_WEBHOOK_SECRET,
        ):
            return False, "Invalid HMAC signature"
    except WebhookSecurityError as e:
        return False, str(e)
    
    # Verify timestamp (if provided)
    try:
        if not verify_timestamp(
            timestamp_header=timestamp_header,
            tolerance_seconds=settings.ZAND_WEBHOOK_TOLERANCE_SECONDS,
        ):
            return False, f"Timestamp outside tolerance window ({settings.ZAND_WEBHOOK_TOLERANCE_SECONDS}s)"
    except WebhookSecurityError as e:
        return False, str(e)
    
    return True, None

