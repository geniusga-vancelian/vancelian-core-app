"""
Transaction model - High-level business transactions
"""

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.core.common.base_model import BaseModel


class TransactionType(str, enum.Enum):
    """Transaction type enum"""
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    INVESTMENT = "INVESTMENT"


class TransactionStatus(str, enum.Enum):
    """Transaction status enum - Derived from Operations by Transaction Status Engine"""
    INITIATED = "INITIATED"  # Transaction created, no Operations completed yet
    COMPLIANCE_REVIEW = "COMPLIANCE_REVIEW"  # DEPOSIT: DEPOSIT_AED completed, awaiting compliance review
    LOCKED = "LOCKED"  # INVESTMENT: Funds locked for investment
    AVAILABLE = "AVAILABLE"  # DEPOSIT: Funds released and available
    FAILED = "FAILED"  # Any Operation failed or deposit rejected
    CANCELLED = "CANCELLED"  # Explicitly cancelled (future)


class Transaction(BaseModel):
    """
    Transaction model - High-level business transaction
    
    A Transaction groups multiple Operations and represents a business action:
    - DEPOSIT: User deposits funds
    - WITHDRAWAL: User withdraws funds
    - INVESTMENT: User invests funds
    
    Transaction.status is computed by Transaction Status Engine based on completed Operations.
    Transaction.status is deterministic and idempotent.
    """

    __tablename__ = "transactions"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", name="fk_transactions_user_id"), nullable=False, index=True)
    type = Column(SQLEnum(TransactionType, name="transaction_type", create_constraint=True), nullable=False, index=True)
    status = Column(SQLEnum(TransactionStatus, name="transaction_status", create_constraint=True), nullable=False, default=TransactionStatus.INITIATED, index=True)
    transaction_metadata = Column("metadata", JSON, nullable=True)  # JSONB in PostgreSQL - flexible metadata storage (column name is "metadata" but attribute is transaction_metadata to avoid SQLAlchemy conflict)

    # Relationships
    user = relationship("User", back_populates="transactions")
    operations = relationship("Operation", back_populates="transaction", lazy="select")
