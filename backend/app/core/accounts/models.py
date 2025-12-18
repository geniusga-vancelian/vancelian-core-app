"""
Account model
"""

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.core.common.base_model import BaseModel


class AccountType(str, enum.Enum):
    """
    Account type enum - Virtual compartments for funds availability
    
    Wallet virtualization: A user's "wallet" is a virtual aggregation of multiple accounts.
    Each account type represents a compartment with different availability rules:
    - WALLET_AVAILABLE: Funds available for use (default)
    - WALLET_BLOCKED: Funds blocked (e.g., pending compliance review)
    - WALLET_LOCKED: Funds locked (e.g., by fraud detection)
    - INTERNAL_OMNIBUS: Internal account for platform operations
    
    Legacy support:
    - WALLET: Backward compatibility (treated as WALLET_AVAILABLE)
    - INTERNAL_BLOCKED: Legacy internal account type
    """
    # Wallet compartments (virtual wallet)
    WALLET = "WALLET"  # Legacy - backward compatibility
    WALLET_AVAILABLE = "WALLET_AVAILABLE"
    WALLET_BLOCKED = "WALLET_BLOCKED"
    WALLET_LOCKED = "WALLET_LOCKED"
    # Internal accounts
    INTERNAL_BLOCKED = "INTERNAL_BLOCKED"  # Legacy
    INTERNAL_OMNIBUS = "INTERNAL_OMNIBUS"


class Account(BaseModel):
    """
    Account model - Represents a virtual compartment for funds in a specific currency
    
    Wallet Virtualization:
    - A "wallet" is a virtual concept, not a single account
    - A user can have multiple accounts per currency (one per account_type)
    - Funds availability is determined by the account_type compartment:
      * WALLET_AVAILABLE: Funds available for user operations
      * WALLET_BLOCKED: Funds blocked (e.g., pending compliance review)
      * WALLET_LOCKED: Funds locked (e.g., fraud prevention)
    
    Balance Calculation:
    - Account balance = SUM(ledger_entries.amount) WHERE account_id = account.id
    - Wallet balance (virtual) = SUM(all account balances) per currency
    
    Fund Movement:
    - Funds move between accounts via LedgerEntry (CREDIT/DEBIT pairs)
    - Example: Moving funds from AVAILABLE to BLOCKED creates:
      * DEBIT entry on WALLET_AVAILABLE account
      * CREDIT entry on WALLET_BLOCKED account
    
    Constraints:
    - One account per (user_id, currency, account_type) combination
    - Account is NEVER modified directly - all changes go through LedgerEntry
    - No balance field stored - always calculated from LedgerEntry
    """

    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint('user_id', 'currency', 'account_type', name='uq_accounts_user_currency_type'),
    )

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", name="fk_accounts_user_id"), nullable=False, index=True)
    currency = Column(String(3), nullable=False, index=True)  # ISO 4217 currency code (e.g., AED, USD)
    account_type = Column(SQLEnum(AccountType, name="account_type", create_constraint=True), nullable=False, default=AccountType.WALLET_AVAILABLE)
    # Note: Account is a read-only representation - balance calculated from LedgerEntry sum
    # updated_at exists but should not be used - account changes go through LedgerEntry

    # Relationships
    user = relationship("User", backref="accounts")
    ledger_entries = relationship("LedgerEntry", back_populates="account", lazy="select")
