"""
Idempotency helpers - placeholder
"""

from typing import Optional
from sqlalchemy.orm import Session
from app.core.ledger.models import Operation


def check_idempotency_key(
    db: Session, idempotency_key: Optional[str], operation_type: str
) -> Optional[Operation]:
    """
    Check if an operation with the same idempotency_key already exists
    Returns existing operation if found, None otherwise
    """
    if not idempotency_key:
        return None

    existing = (
        db.query(Operation)
        .filter(
            Operation.idempotency_key == idempotency_key,
            Operation.type == operation_type,
        )
        .first()
    )

    return existing

