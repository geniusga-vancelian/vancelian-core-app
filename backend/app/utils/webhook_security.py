"""
Webhook security utilities - HMAC signature verification and replay protection
"""

import hmac
import hashlib
import time
import logging
from typing import Optional, Tuple, Dict, Any
from fastapi import HTTPException, status

from app.infrastructure.settings import get_settings

logger = logging.getLogger(__name__)


class WebhookSecurityError(Exception):
    """Raised when webhook security verification fails"""
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


def verify_hmac_signature(
    payload_body: bytes,
    signature_header: str,
    secret: str,
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Verify HMAC-SHA256 signature using constant-time comparison.
    
    The signature is computed over EXACT raw request body bytes (canonical representation).
    
    Args:
        payload_body: Raw request body (bytes) - EXACT bytes as received
        signature_header: Signature from X-Zand-Signature header
        secret: Shared secret key
    
    Returns:
        Tuple of (is_valid, error_code, error_details)
        - is_valid: True if signature is valid
        - error_code: Error code if invalid (None if valid)
        - error_details: Dict with error details (None if valid)
    """
    if not secret:
        return False, "WEBHOOK_INVALID_SIGNATURE", {
            "reason": "ZAND_WEBHOOK_SECRET not configured",
            "hint": "Set ZAND_WEBHOOK_SECRET in environment variables"
        }
    
    if not signature_header:
        return False, "WEBHOOK_MISSING_HEADER", {
            "missing_header": "X-Zand-Signature",
            "hint": "Include X-Zand-Signature header with HMAC-SHA256 signature of request body"
        }
    
    # Compute expected signature over raw body bytes
    # Signature is computed over EXACT raw request body bytes (canonical representation)
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload_body,  # Raw body bytes (not re-serialized JSON)
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(expected_signature, signature_header):
        return False, "WEBHOOK_INVALID_SIGNATURE", {
            "expected_length": len(expected_signature),
            "received_length": len(signature_header),
            "expected_preview": expected_signature[:8] + "..." if len(expected_signature) > 8 else expected_signature,
            "received_preview": signature_header[:8] + "..." if len(signature_header) > 8 else signature_header,
            "body_length_bytes": len(payload_body),
            "hint": f"Signature mismatch. Ensure signature is computed over exact raw body bytes (HMAC-SHA256). Body length: {len(payload_body)} bytes"
        }
    
    return True, None, None


def verify_timestamp(
    timestamp_header: Optional[str],
    tolerance_seconds: int,
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Verify timestamp to prevent replay attacks.
    
    Args:
        timestamp_header: Timestamp from X-Zand-Timestamp header (Unix timestamp as string)
        tolerance_seconds: Maximum allowed time difference in seconds
    
    Returns:
        Tuple of (is_valid, error_code, error_details)
        - is_valid: True if timestamp is within tolerance
        - error_code: Error code if invalid (None if valid or not provided)
        - error_details: Dict with error details (None if valid)
    """
    if not timestamp_header:
        # If no timestamp provided, rely on strict idempotency only
        logger.debug("No timestamp header provided - relying on idempotency protection")
        return True, None, None
    
    try:
        timestamp = int(timestamp_header)
    except (ValueError, TypeError):
        return False, "WEBHOOK_INVALID_TIMESTAMP", {
            "received": timestamp_header,
            "expected_format": "Unix timestamp (integer as string)",
            "hint": "X-Zand-Timestamp must be a valid Unix timestamp (seconds since epoch)"
        }
    
    current_time = int(time.time())
    time_delta = abs(current_time - timestamp)
    
    if time_delta > tolerance_seconds:
        return False, "WEBHOOK_TIMESTAMP_SKEW", {
            "received_timestamp": timestamp,
            "current_timestamp": current_time,
            "time_delta_seconds": time_delta,
            "max_skew_seconds": tolerance_seconds,
            "hint": f"Timestamp is {time_delta}s from current time (max allowed: {tolerance_seconds}s). Check system clock or regenerate request."
        }
    
    return True, None, None


def verify_zand_webhook_security(
    payload_body: bytes,
    signature_header: Optional[str],
    timestamp_header: Optional[str] = None,
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Complete webhook security verification for ZAND Bank webhooks.
    
    Performs:
    1. HMAC-SHA256 signature verification (over exact raw body bytes)
    2. Timestamp/replay protection (if timestamp provided)
    
    Args:
        payload_body: Raw request body (bytes) - EXACT bytes as received (canonical)
        signature_header: Signature from X-Zand-Signature header
        timestamp_header: Optional timestamp from X-Zand-Timestamp header
    
    Returns:
        Tuple of (is_valid, error_code, error_details)
        - is_valid: True if all checks pass
        - error_code: Error code if verification fails (None if valid)
        - error_details: Dict with error details (None if valid)
    """
    settings = get_settings()
    
    # Check signature header is present
    if not signature_header:
        return False, "WEBHOOK_MISSING_HEADER", {
            "missing_header": "X-Zand-Signature",
            "hint": "Include X-Zand-Signature header with HMAC-SHA256 signature of request body"
        }
    
    # Verify HMAC signature
    is_valid, error_code, error_details = verify_hmac_signature(
        payload_body=payload_body,
        signature_header=signature_header,
        secret=settings.ZAND_WEBHOOK_SECRET,
    )
    if not is_valid:
        return False, error_code, error_details
    
    # Verify timestamp (if provided)
    is_valid, error_code, error_details = verify_timestamp(
        timestamp_header=timestamp_header,
        tolerance_seconds=settings.ZAND_WEBHOOK_TOLERANCE_SECONDS,
    )
    if not is_valid:
        return False, error_code, error_details
    
    return True, None, None


