"""
Vault models - Cash-only vaults (coffres)
"""

from decimal import Decimal
from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, Numeric, Text, DateTime, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.core.common.base_model import BaseModel


class VaultStatus(str, enum.Enum):
    """Vault status enum"""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"


class WithdrawalRequestStatus(str, enum.Enum):
    """Withdrawal request status enum"""
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"


class Vault(BaseModel):
    """
    Vault model - Represents a cash-only vault (coffre)
    
    Examples: FLEX (liquid), AVENIR (locked for X days)
    
    Note: cash_balance and total_aum are deprecated fields.
    They should be derived from the ledger (vault pool account balance)
    and sum of vault_accounts.principal respectively.
    """
    
    __tablename__ = "vaults"
    
    code = Column(String(50), unique=True, nullable=False, index=True)  # Short code like "FLEX", "AVENIR"
    name = Column(String(255), nullable=False)  # Display name like "FLEX - Flexible Vault"
    status = Column(SQLEnum(VaultStatus, name="vault_status", create_constraint=True), nullable=False, default=VaultStatus.ACTIVE, index=True)
    
    # Deprecated: Use ledger for cash_balance (vault pool account balance)
    cash_balance = Column(Numeric(20, 2), nullable=False, default=Decimal("0.00"))
    # Deprecated: Use sum of vault_accounts.principal for total_aum
    total_aum = Column(Numeric(20, 2), nullable=False, default=Decimal("0.00"))
    
    # Lock configuration (for AVENIR vault)
    locked_until = Column(DateTime(timezone=True), nullable=True)  # Lock all withdrawals until this date
    
    # Relationships
    accounts = relationship("VaultAccount", back_populates="vault", cascade="all, delete-orphan")
    withdrawal_requests = relationship("WithdrawalRequest", back_populates="vault", cascade="all, delete-orphan")


class VaultAccount(BaseModel):
    """
    VaultAccount model - User's account in a vault
    
    Tracks user's principal (deposits) and available balance (principal - pending withdrawals).
    """
    
    __tablename__ = "vault_accounts"
    
    vault_id = Column(UUID(as_uuid=True), ForeignKey("vaults.id", name="fk_vault_accounts_vault_id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", name="fk_vault_accounts_user_id"), nullable=False, index=True)
    
    principal = Column(Numeric(20, 2), nullable=False, default=Decimal("0.00"))  # Total deposits (never decreases except on withdrawal)
    available_balance = Column(Numeric(20, 2), nullable=False, default=Decimal("0.00"))  # Available for withdrawal (principal - pending withdrawals)
    
    locked_until = Column(DateTime(timezone=True), nullable=True)  # Lock withdrawals until this date (per-user lock, e.g., AVENIR)
    
    # Unique constraint: one account per user per vault
    __table_args__ = (
        UniqueConstraint('vault_id', 'user_id', name='uq_vault_accounts_vault_user'),
        Index('ix_vault_accounts_vault_user', 'vault_id', 'user_id'),
    )
    
    # Relationships
    vault = relationship("Vault", back_populates="accounts")
    user = relationship("User", foreign_keys=[user_id])


class WithdrawalRequest(BaseModel):
    """
    WithdrawalRequest model - FIFO queue for vault withdrawals
    
    When vault has insufficient cash, withdrawals are queued as PENDING.
    Admin process_pending_withdrawals processes them in FIFO order.
    """
    
    __tablename__ = "withdrawal_requests"
    
    vault_id = Column(UUID(as_uuid=True), ForeignKey("vaults.id", name="fk_withdrawal_requests_vault_id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", name="fk_withdrawal_requests_user_id"), nullable=False, index=True)
    
    amount = Column(Numeric(20, 2), nullable=False)  # Withdrawal amount
    status = Column(SQLEnum(WithdrawalRequestStatus, name="withdrawal_request_status", create_constraint=True), nullable=False, default=WithdrawalRequestStatus.PENDING, index=True)
    reason = Column(Text, nullable=True)  # Optional reason/note
    
    executed_at = Column(DateTime(timezone=True), nullable=True)  # Timestamp when status changed to EXECUTED
    
    # Table constraints
    __table_args__ = (
        CheckConstraint('amount > 0', name='ck_withdrawal_requests_amount_positive'),
        Index('ix_withdrawal_requests_vault_status_created', 'vault_id', 'status', 'created_at'),  # For FIFO processing
    )
    
    # Relationships
    vault = relationship("Vault", back_populates="withdrawal_requests")
    user = relationship("User", foreign_keys=[user_id])
