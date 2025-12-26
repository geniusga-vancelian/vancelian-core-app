"""
Account model - Wallet compartments and system accounts
"""

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.core.common.base_model import BaseModel


class AccountType(str, enum.Enum):
    """Account type enum"""
    WALLET_AVAILABLE = "WALLET_AVAILABLE"  # User's available balance
    WALLET_BLOCKED = "WALLET_BLOCKED"  # User's blocked balance (pending compliance review)
    WALLET_LOCKED = "WALLET_LOCKED"  # User's locked balance (locked for investment)
    INTERNAL_OMNIBUS = "INTERNAL_OMNIBUS"  # System-wide omnibus account (not user-specific)
    VAULT_POOL_CASH = "VAULT_POOL_CASH"  # Vault pool cash account (system account, scoped to vault_id) - AVAILABLE bucket
    VAULT_POOL_LOCKED = "VAULT_POOL_LOCKED"  # Vault pool locked account (system account, scoped to vault_id)
    VAULT_POOL_BLOCKED = "VAULT_POOL_BLOCKED"  # Vault pool blocked account (system account, scoped to vault_id)
    OFFER_POOL_AVAILABLE = "OFFER_POOL_AVAILABLE"  # Offer pool available account (system account, scoped to offer_id)
    OFFER_POOL_LOCKED = "OFFER_POOL_LOCKED"  # Offer pool locked account (system account, scoped to offer_id)
    OFFER_POOL_BLOCKED = "OFFER_POOL_BLOCKED"  # Offer pool blocked account (system account, scoped to offer_id)


class Account(BaseModel):
    """
    Account model - Represents wallet compartments and system accounts
    
    Accounts are immutable (no updated_at) - balance is computed from LedgerEntries.
    Each user has multiple accounts per currency (one per AccountType).
    System accounts (INTERNAL_OMNIBUS) have user_id=None.
    """

    __tablename__ = "accounts"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", name="fk_accounts_user_id"), nullable=True, index=True)
    currency = Column(String(3), nullable=False, index=True)  # ISO 4217 currency code (e.g., AED, USD)
    account_type = Column(SQLEnum(AccountType, name="account_type", create_constraint=True), nullable=False, index=True)
    vault_id = Column(UUID(as_uuid=True), ForeignKey("vaults.id", name="fk_accounts_vault_id"), nullable=True, index=True)  # For VAULT_POOL_* accounts, links to vault
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id", name="fk_accounts_offer_id"), nullable=True, index=True)  # For OFFER_POOL_* accounts, links to offer
    
    # Note: updated_at exists in BaseModel but MUST NOT be used - accounts are immutable
    # Balance is computed from LedgerEntries: SUM(ledger_entries.amount) WHERE account_id = account.id
    
    # Note: vault_id is only used when account_type starts with VAULT_POOL_*. For other account types, vault_id should be NULL.
    # Note: offer_id is only used when account_type starts with OFFER_POOL_*. For other account types, offer_id should be NULL.

    # Relationships
    user = relationship("User", back_populates="accounts")
    vault = relationship("Vault", foreign_keys=[vault_id], lazy="select")  # Forward reference - Vault imported after Account
    offer = relationship("Offer", foreign_keys=[offer_id], lazy="select")  # Forward reference - Offer imported after Account
    ledger_entries = relationship("LedgerEntry", back_populates="account", lazy="select")
    
    # Composite indexes and unique constraint
    # Note: Indexes are also created by Alembic migrations, so they may already exist.
    # SQLAlchemy will handle this gracefully in most cases, but tests may need special handling.
    __table_args__ = (
        Index('ix_accounts_type_vault_currency', 'account_type', 'vault_id', 'currency'),
        Index('ix_accounts_type_offer_currency', 'account_type', 'offer_id', 'currency'),
        # Note: ix_accounts_offer_id is created via Column(..., index=True) above
        # Unique constraint to prevent duplicate accounts
        # Note: In PostgreSQL, NULL != NULL, so this constraint allows multiple rows with NULL values.
        # We rely on application-level "get or create" logic to prevent duplicates.
        UniqueConstraint('account_type', 'user_id', 'vault_id', 'offer_id', 'currency', name='uq_accounts_unique'),
    )
