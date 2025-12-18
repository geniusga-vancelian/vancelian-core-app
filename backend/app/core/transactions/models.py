"""
Transaction model - Saga layer for user-visible flows
"""

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.core.common.base_model import BaseModel


class TransactionType(str, enum.Enum):
    """Transaction type enum - User-facing transaction types"""
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    INVESTMENT = "INVESTMENT"


class TransactionStatus(str, enum.Enum):
    """Transaction status enum - Status of the user-facing transaction saga"""
    INITIATED = "INITIATED"
    COMPLIANCE_REVIEW = "COMPLIANCE_REVIEW"
    AVAILABLE = "AVAILABLE"
    LOCKED = "LOCKED"  # Funds locked for investment
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Transaction(BaseModel):
    """
    Transaction model - Saga layer representing user-visible flows
    
    A Transaction represents a user-facing saga composed of multiple Operations.
    Example: A DEPOSIT transaction may include:
    - Operation: KYC_VALIDATION
    - Operation: DEPOSIT_AED
    
    Transaction status evolves based on the status of its Operations.
    Transaction is mutable (status can change) but Operations and LedgerEntry remain immutable.
    
    Key differences:
    - Transaction: User-facing, status can evolve, represents a saga/flow
    - Operation: Immutable, audit-proof, represents business meaning of an action
    - LedgerEntry: Immutable, accounting-only, represents financial movement
    """

    __tablename__ = "transactions"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", name="fk_transactions_user_id"), nullable=False, index=True)
    type = Column(SQLEnum(TransactionType, name="transaction_type", create_constraint=True), nullable=False, index=True)
    status = Column(SQLEnum(TransactionStatus, name="transaction_status", create_constraint=True), nullable=False, default=TransactionStatus.INITIATED, index=True)
    external_reference = Column(String(255), nullable=True, index=True)  # e.g., ZAND Bank reference
    metadata = Column(JSON, nullable=True)  # JSONB in PostgreSQL - flexible metadata storage

    # Relationships
    user = relationship("User", backref="transactions")
    operations = relationship("Operation", back_populates="transaction", lazy="select")

