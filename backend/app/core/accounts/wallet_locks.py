"""
WalletLock model - Tracks locked funds with reason and reference (liability tracking)

This model provides a metadata layer on top of ledger entries to track:
- Which funds are locked for which instrument (Offer/Vault)
- The reason for the lock (OFFER_INVEST, VAULT_AVENIR_VESTING, etc.)
- Idempotency via intent_id or operation_id

This is the source of truth for Wallet Matrix OFFER_USER and VAULT_USER rows.
"""
from decimal import Decimal
from sqlalchemy import Column, String, ForeignKey, Numeric, Text, DateTime, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.core.common.base_model import BaseModel


class LockReason(str, enum.Enum):
    """Lock reason enum"""
    OFFER_INVEST = "OFFER_INVEST"  # Funds locked for investment in an offer
    VAULT_AVENIR_VESTING = "VAULT_AVENIR_VESTING"  # Funds locked in AVENIR vault (vesting period)
    # Future: other reasons can be added here


class ReferenceType(str, enum.Enum):
    """Reference type enum"""
    OFFER = "OFFER"  # Reference to an Offer
    VAULT = "VAULT"  # Reference to a Vault
    # Future: other types can be added here


class LockStatus(str, enum.Enum):
    """Lock status enum"""
    ACTIVE = "ACTIVE"  # Lock is active (funds are locked)
    RELEASED = "RELEASED"  # Lock has been released (funds unlocked, e.g., offer closed, withdrawal)


class WalletLock(BaseModel):
    """
    WalletLock model - Tracks locked funds with reason and reference
    
    This is a metadata layer that tracks which funds in WALLET_LOCKED are attributed
    to which instrument (Offer/Vault) and why. This enables:
    - Wallet Matrix to show instrument-level exposure
    - Admin views to see total liabilities per offer
    - Idempotency (prevent double-counting same investment)
    
    The actual funds movement is tracked in the ledger (LedgerEntry).
    This model provides the "why" and "where" metadata.
    """
    
    __tablename__ = "wallet_locks"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", name="fk_wallet_locks_user_id"), nullable=False, index=True)
    currency = Column(String(3), nullable=False, default="AED", index=True)  # ISO 4217
    amount = Column(Numeric(20, 2), nullable=False)  # Locked amount
    
    reason = Column(String(50), nullable=False, index=True)  # Lock reason (OFFER_INVEST, VAULT_AVENIR_VESTING, etc.)
    reference_type = Column(String(20), nullable=False, index=True)  # Reference type (OFFER, VAULT)
    reference_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # Reference to offer_id or vault_id
    
    status = Column(String(20), nullable=False, default=LockStatus.ACTIVE.value, index=True)  # ACTIVE or RELEASED
    
    # Idempotency: link to InvestmentIntent (preferred) or Operation
    intent_id = Column(UUID(as_uuid=True), ForeignKey("investment_intents.id", name="fk_wallet_locks_intent_id"), nullable=True, unique=True, index=True)  # For idempotency: one lock per intent
    operation_id = Column(UUID(as_uuid=True), ForeignKey("operations.id", name="fk_wallet_locks_operation_id"), nullable=True, index=True)  # Link to ledger operation
    
    released_at = Column(DateTime(timezone=True), nullable=True)  # When lock was released (if status=RELEASED)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], lazy="select")
    intent = relationship("InvestmentIntent", foreign_keys=[intent_id], lazy="select")
    operation = relationship("Operation", foreign_keys=[operation_id], lazy="select")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint('amount > 0', name='check_wallet_locks_amount_positive'),
        Index('ix_wallet_locks_reference', 'reference_type', 'reference_id', 'reason', 'status'),
        Index('ix_wallet_locks_user_status', 'user_id', 'status'),
        # Unique constraint for idempotency: one active lock per intent_id
        # Note: intent_id is already unique (unique=True on column), but we add this for clarity
        # If intent_id is NULL, we can't use it for idempotency, so we rely on application logic
    )

