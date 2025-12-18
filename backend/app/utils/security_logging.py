"""
Security event logging and audit
"""

import logging
import time
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.infrastructure.logging_config import trace_id_context
from app.infrastructure.redis_client import get_redis
from app.core.compliance.models import AuditLog
from app.core.security.models import Role

logger = logging.getLogger(__name__)


def log_security_event(
    action: str,
    details: Dict[str, Any],
    trace_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> None:
    """
    Log a security event and optionally write AuditLog.
    
    Args:
        action: Security action (e.g., "RATE_LIMIT_EXCEEDED", "WEBHOOK_SIGNATURE_FAILED")
        details: Event details (will be sanitized to remove secrets)
        trace_id: Optional trace ID (will try to get from context if not provided)
        db: Optional database session for AuditLog write
    """
    # Get trace_id from context if not provided
    if not trace_id:
        trace_id = trace_id_context.get("unknown")
    
    # Sanitize details (remove secrets)
    sanitized_details = _sanitize_details(details)
    
    # Log security event
    logger.warning(
        f"Security event: action={action}, trace_id={trace_id}, details={sanitized_details}"
    )
    
    # Write AuditLog if database session provided
    if db:
        try:
            audit_log = AuditLog(
                actor_user_id=None,  # System event
                actor_role=Role.OPS,
                action=action,
                entity_type="Security",
                entity_id=None,
                before=None,
                after=sanitized_details,
                reason=f"Security event: {action}",
            )
            db.add(audit_log)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to write AuditLog for security event: {e}")
            db.rollback()


def _sanitize_details(details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize details dictionary to remove secrets.
    
    Removes fields that might contain sensitive information.
    """
    sensitive_keys = {
        "secret", "password", "token", "api_key", "signature",
        "authorization", "x-signature", "x-zand-signature",
    }
    
    sanitized = {}
    for key, value in details.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            sanitized[key] = "[REDACTED]"
        else:
            sanitized[key] = value
    
    return sanitized


def track_abuse_pattern(
    redis_client,
    endpoint_group: str,
    identifier: str,
    threshold: int = 5,
    window_seconds: int = 600,  # 10 minutes
) -> bool:
    """
    Track repeated abuse patterns (e.g., repeated rate limit blocks).
    
    Args:
        redis_client: Redis client
        endpoint_group: Endpoint group (webhook, admin, api)
        identifier: Client identifier (typically IP)
        threshold: Number of violations to trigger abuse detection
        window_seconds: Time window for threshold (default: 10 minutes)
    
    Returns:
        True if abuse pattern detected, False otherwise
    """
    key = f"abuse:{endpoint_group}:{identifier}"
    now = int(time.time())
    window_start = now - window_seconds
    
    # Clean old entries
    redis_client.zremrangebyscore(key, 0, window_start)
    
    # Increment counter
    redis_client.zadd(key, {str(now): now})
    redis_client.expire(key, window_seconds + 10)
    
    # Count violations in window
    count = redis_client.zcard(key)
    
    if count >= threshold:
        logger.error(
            f"Abuse pattern detected: endpoint_group={endpoint_group}, "
            f"identifier={identifier}, violations={count} in {window_seconds}s"
        )
        return True
    
    return False


def log_repeated_abuse(
    endpoint_group: str,
    identifier: str,
    violation_count: int,
    trace_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> None:
    """
    Log repeated abuse detection and write AuditLog.
    
    Called when abuse pattern is detected (repeated rate limit blocks).
    """
    if not trace_id:
        trace_id = trace_id_context.get("unknown")
    
    details = {
        "endpoint_group": endpoint_group,
        "identifier": identifier,
        "violation_count": violation_count,
        "severity": "HIGH",
    }
    
    logger.error(
        f"Repeated abuse detected: endpoint_group={endpoint_group}, "
        f"identifier={identifier}, violations={violation_count}, trace_id={trace_id}"
    )
    
    if db:
        try:
            audit_log = AuditLog(
                actor_user_id=None,
                actor_role=Role.OPS,
                action="REPEATED_ABUSE_DETECTED",
                entity_type="Security",
                entity_id=None,
                before=None,
                after=details,
                reason=f"Repeated abuse detected: {violation_count} violations in 10 minutes",
            )
            db.add(audit_log)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to write AuditLog for abuse detection: {e}")
            db.rollback()



