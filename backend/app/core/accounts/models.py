"""
Account model - Wallet compartments and system accounts
"""

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum
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
    
    # Note: updated_at exists in BaseModel but MUST NOT be used - accounts are immutable
    # Balance is computed from LedgerEntries: SUM(ledger_entries.amount) WHERE account_id = account.id

    # Relationships
    user = relationship("User", back_populates="accounts")
    ledger_entries = relationship("LedgerEntry", back_populates="account", lazy="select")
