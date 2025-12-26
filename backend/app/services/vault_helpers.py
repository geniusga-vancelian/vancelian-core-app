"""
Vault account helpers
"""

from decimal import Decimal
from uuid import UUID
from sqlalchemy.orm import Session
from app.core.accounts.models import Account, AccountType
from app.services.wallet_helpers import ensure_wallet_accounts, get_account_balance


def get_user_wallet_available_account(db: Session, user_id: UUID, currency: str) -> UUID:
    """
    Get user's WALLET_AVAILABLE account ID.
    
    Creates account if it doesn't exist.
    
    Returns:
        UUID: Account ID for WALLET_AVAILABLE
    """
    wallet_accounts = ensure_wallet_accounts(db, user_id, currency)
    return wallet_accounts[AccountType.WALLET_AVAILABLE.value]


def get_or_create_vault_pool_cash_account(db: Session, vault_id: UUID, currency: str) -> UUID:
    """
    Get or create vault pool cash account (VAULT_POOL_CASH account type).
    
    Vault pool accounts are system accounts (user_id=None) with vault_id set.
    
    Returns:
        UUID: Account ID for VAULT_POOL_CASH account
    """
    # Find existing account
    account = db.query(Account).filter(
        Account.account_type == AccountType.VAULT_POOL_CASH,
        Account.vault_id == vault_id,
        Account.currency == currency,
        Account.user_id.is_(None),  # System account
    ).first()
    
    if account:
        return account.id
    
    # Create new vault pool cash account
    account = Account(
        user_id=None,  # System account (no user)
        currency=currency,
        account_type=AccountType.VAULT_POOL_CASH,
        vault_id=vault_id,
    )
    db.add(account)
    db.flush()  # Flush to get the ID
    
    return account.id


def get_vault_cash_balance(db: Session, vault_id: UUID, currency: str) -> Decimal:
    """
    Get vault cash balance from ledger (source of truth).
    
    Returns the balance of the vault pool cash account.
    
    Returns:
        Decimal: Vault pool cash balance (can be negative)
    """
    account_id = get_or_create_vault_pool_cash_account(db, vault_id, currency)
    return get_account_balance(db, account_id)
