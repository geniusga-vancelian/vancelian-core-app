"""
Vault models - Cash-only vaults (coffres)
"""

from decimal import Decimal
from datetime import date, timedelta
from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, Numeric, Text, DateTime, Date, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
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


class VestingLotStatus(str, enum.Enum):
    """Vesting lot status enum"""
    VESTED = "VESTED"  # Lot verrouillé, pas encore mature ou partiellement libéré
    RELEASED = "RELEASED"  # Lot entièrement libéré
    CANCELLED = "CANCELLED"  # Lot annulé (ex: coffre fermé)


class VestingLot(BaseModel):
    """
    VestingLot model - Tracks vesting lots for AVENIR vault deposits
    
    Each deposit in AVENIR creates exactly one vesting lot with:
    - deposit_day: Date normalisée à minuit UTC du dépôt
    - release_day: Date normalisée à minuit UTC de maturité (deposit_day + 365 jours)
    - amount: Montant original du dépôt (immuable)
    - released_amount: Montant déjà libéré (0 <= released_amount <= amount)
    - status: VESTED, RELEASED, ou CANCELLED
    
    Idempotence: UNIQUE(source_operation_id) garantit qu'un dépôt ne crée qu'un seul lot.
    """
    
    __tablename__ = "vault_vesting_lots"
    
    # Références
    vault_id = Column(UUID(as_uuid=True), ForeignKey("vaults.id", name="fk_vault_vesting_lots_vault_id", ondelete="CASCADE"), nullable=False, index=True)
    vault_code = Column(String(50), nullable=False, index=True)  # Denormalized pour queries (ex: "AVENIR")
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", name="fk_vault_vesting_lots_user_id", ondelete="CASCADE"), nullable=False, index=True)
    currency = Column(String(3), nullable=False, default="AED", index=True)  # ISO 4217
    
    # Période de vesting
    deposit_day = Column(Date, nullable=False)  # Date normalisée à minuit UTC
    release_day = Column(Date, nullable=False)  # Date normalisée à minuit UTC (deposit_day + 365)
    
    # Montants
    amount = Column(Numeric(20, 2), nullable=False)  # Montant original du dépôt (immuable)
    released_amount = Column(Numeric(20, 2), nullable=False, default=Decimal("0.00"))  # Montant déjà libéré
    
    # État
    status = Column(String(20), nullable=False, default=VestingLotStatus.VESTED.value, index=True)  # VESTED, RELEASED, CANCELLED
    
    # Traçabilité
    source_operation_id = Column(UUID(as_uuid=True), ForeignKey("operations.id", name="fk_vault_vesting_lots_source_operation_id"), nullable=False, unique=True, index=True)  # Opération de dépôt originale
    last_released_at = Column(DateTime(timezone=True), nullable=True)  # Timestamp du dernier release
    last_release_operation_id = Column(UUID(as_uuid=True), ForeignKey("operations.id", name="fk_vault_vesting_lots_last_release_operation_id"), nullable=True)  # Dernière opération de release
    
    # Idempotence pour job de release
    release_job_trace_id = Column(UUID(as_uuid=True), nullable=True)  # Trace ID du dernier run qui a traité le lot
    release_job_run_at = Column(DateTime(timezone=True), nullable=True)  # Timestamp du dernier run
    
    # Métadonnées extensibles
    lot_metadata = Column(JSONB, nullable=True, name="metadata")  # JSONB pour règles futures: release schedule, custom rules, etc. (DB column name: metadata, Python attr: lot_metadata to avoid SQLAlchemy conflict)
    
    # Relationships
    vault = relationship("Vault", foreign_keys=[vault_id], lazy="select")
    user = relationship("User", foreign_keys=[user_id], lazy="select")
    source_operation = relationship("Operation", foreign_keys=[source_operation_id], lazy="select")
    last_release_operation = relationship("Operation", foreign_keys=[last_release_operation_id], lazy="select")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint('amount > 0', name='ck_vault_vesting_lots_amount_positive'),
        CheckConstraint('released_amount >= 0 AND released_amount <= amount', name='ck_vault_vesting_lots_released_amount_valid'),
        CheckConstraint(
            "(status = 'RELEASED' AND released_amount = amount) OR (status != 'RELEASED')",
            name='ck_vault_vesting_lots_status_released'
        ),
        Index('ix_vault_vesting_lots_vault_user', 'vault_id', 'user_id'),
        Index('ix_vault_vesting_lots_release_day_status', 'release_day', 'status'),
        Index('ix_vault_vesting_lots_user_status', 'user_id', 'status'),
        Index('ix_vault_vesting_lots_source_operation', 'source_operation_id'),
        Index('ix_vault_vesting_lots_vault_code_release_day', 'vault_code', 'release_day', 'status'),
        UniqueConstraint('source_operation_id', name='uq_vault_vesting_lots_source_operation'),
    )
    
    @hybrid_property
    def remaining_amount(self) -> Decimal:
        """Montant restant à libérer (calculé)"""
        return self.amount - self.released_amount
    
    def __repr__(self) -> str:
        return f"<VestingLot(id={self.id}, vault_code={self.vault_code}, user_id={self.user_id}, amount={self.amount}, released_amount={self.released_amount}, status={self.status})>"
