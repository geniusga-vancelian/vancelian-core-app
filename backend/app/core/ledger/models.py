"""
Ledger models - Operation and LedgerEntry (IMMUTABLE)
"""

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, Numeric, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.core.common.base_model import BaseModel


class OperationType(str, enum.Enum):
    """Operation type enum"""
    DEPOSIT_AED = "DEPOSIT_AED"
    INVEST_EXCLUSIVE = "INVEST_EXCLUSIVE"
    RELEASE_FUNDS = "RELEASE_FUNDS"
    REVERSAL_DEPOSIT = "REVERSAL_DEPOSIT"  # Reversal of deposit (rejection)
    ADJUSTMENT = "ADJUSTMENT"
    REVERSAL = "REVERSAL"  # Generic reversal


class OperationStatus(str, enum.Enum):
    """Operation status enum"""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class LedgerEntryType(str, enum.Enum):
    """Ledger entry type enum"""
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class Operation(BaseModel):
    """
    Operation model - Represents the business meaning of an action
    Groups multiple LedgerEntry and always audited
    
    An Operation is immutable and audit-proof. It may be part of a Transaction saga.
    Operations never change status after COMPLETED - corrections use new Operations (ADJUSTMENT/REVERSAL).
    """

    __tablename__ = "operations"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", name="fk_operations_transaction_id"), nullable=True, index=True)
    type = Column(SQLEnum(OperationType, name="operation_type", create_constraint=True), nullable=False, index=True)
    status = Column(SQLEnum(OperationStatus, name="operation_status", create_constraint=True), nullable=False, default=OperationStatus.PENDING, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    operation_metadata = Column(JSON, nullable=True)  # JSONB in PostgreSQL - flexible metadata storage (renamed from metadata to avoid SQLAlchemy conflict)

    # Relationships
    transaction = relationship("Transaction", back_populates="operations")
    ledger_entries = relationship("LedgerEntry", back_populates="operation", lazy="select")


class LedgerEntry(BaseModel):
    """
    LedgerEntry model - IMMUTABLE (WRITE-ONCE)
    
    Each financial movement creates a ledger line.
    
    IMMUTABILITY RULES (application-level):
    - ❌ NEVER UPDATE a LedgerEntry
    - ❌ NEVER DELETE a LedgerEntry
    - ✅ Corrections must be done via a new Operation (ADJUSTMENT or REVERSAL)
    
    The balance of an Account = SUM(ledger_entries.amount) WHERE account_id = account.id
    
    This model enforces immutability at the application level by:
    - Not having an updated_at field
    - Not providing update/delete methods in repositories
    - Requiring all modifications through Operation workflow
    
    Future database-level enforcement (documented, not implemented):
    - PostgreSQL triggers to block UPDATE/DELETE on ledger_entries table
    - Or use views with INSTEAD OF triggers for write operations
    """

    __tablename__ = "ledger_entries"

    operation_id = Column(UUID(as_uuid=True), ForeignKey("operations.id", name="fk_ledger_entries_operation_id"), nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", name="fk_ledger_entries_account_id"), nullable=False, index=True)
    amount = Column(Numeric(24, 8), nullable=False)  # Positive or negative (precision for financial data)
    currency = Column(String(3), nullable=False)  # ISO 4217 currency code (e.g., AED, USD)
    entry_type = Column(SQLEnum(LedgerEntryType, name="ledger_entry_type", create_constraint=True), nullable=False, index=True)
    # Note: updated_at exists in BaseModel but MUST NOT be used - entries are immutable (write-once)

    # Relationships
    operation = relationship("Operation", back_populates="ledger_entries")
    account = relationship("Account", back_populates="ledger_entries")

