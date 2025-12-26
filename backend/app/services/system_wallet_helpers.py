"""
System wallet helpers - Ensure system wallets exist for Offers and Vaults

System wallets are accounts with user_id=None, scoped by offer_id or vault_id.
They have 3 buckets: AVAILABLE, LOCKED, BLOCKED.
"""
from decimal import Decimal
from typing import Dict
from uuid import UUID
from sqlalchemy.orm import Session
from app.core.accounts.models import Account, AccountType
from app.services.wallet_helpers import get_account_balance


def get_or_create_offer_pool_account(
    db: Session,
    offer_id: UUID,
    currency: str,
    bucket_account_type: AccountType,
) -> UUID:
    """
    Get or create a specific bucket account for an offer system wallet.
    
    Args:
        db: Database session
        offer_id: Offer UUID
        currency: Currency code (e.g., "AED")
        bucket_account_type: AccountType for the bucket (OFFER_POOL_AVAILABLE, OFFER_POOL_LOCKED, or OFFER_POOL_BLOCKED)
    
    Returns:
        UUID: Account ID
    """
    # Validate bucket_account_type
    if bucket_account_type not in [
        AccountType.OFFER_POOL_AVAILABLE,
        AccountType.OFFER_POOL_LOCKED,
        AccountType.OFFER_POOL_BLOCKED,
    ]:
        raise ValueError(f"Invalid bucket_account_type for offer pool: {bucket_account_type}")
    
    # Find existing account
    account = db.query(Account).filter(
        Account.account_type == bucket_account_type,
        Account.offer_id == offer_id,
        Account.currency == currency,
        Account.user_id.is_(None),  # System account
        Account.vault_id.is_(None),  # Not a vault account
    ).first()
    
    if account:
        return account.id
    
    # Create new account
    account = Account(
        user_id=None,  # System account
        currency=currency,
        account_type=bucket_account_type,
        offer_id=offer_id,
        vault_id=None,
    )
    db.add(account)
    db.flush()  # Flush to get the ID
    
    return account.id


def ensure_offer_system_wallet(
    db: Session,
    offer_id: UUID,
    currency: str,
) -> Dict[str, UUID]:
    """
    Ensure all 3 buckets exist for an offer system wallet.
    
    Creates:
    - OFFER_POOL_AVAILABLE
    - OFFER_POOL_LOCKED
    - OFFER_POOL_BLOCKED
    
    Args:
        db: Database session
        offer_id: Offer UUID
        currency: Currency code (e.g., "AED")
    
    Returns:
        Dict mapping bucket names to account IDs:
        {
            "available": UUID,
            "locked": UUID,
            "blocked": UUID,
        }
    """
    available_id = get_or_create_offer_pool_account(
        db, offer_id, currency, AccountType.OFFER_POOL_AVAILABLE
    )
    locked_id = get_or_create_offer_pool_account(
        db, offer_id, currency, AccountType.OFFER_POOL_LOCKED
    )
    blocked_id = get_or_create_offer_pool_account(
        db, offer_id, currency, AccountType.OFFER_POOL_BLOCKED
    )
    
    return {
        "available": available_id,
        "locked": locked_id,
        "blocked": blocked_id,
    }


def get_or_create_vault_pool_account(
    db: Session,
    vault_id: UUID,
    currency: str,
    account_type: AccountType,
) -> UUID:
    """
    Get or create a specific bucket account for a vault system wallet.
    
    Args:
        db: Database session
        vault_id: Vault UUID
        currency: Currency code (e.g., "AED")
        account_type: AccountType for the bucket (VAULT_POOL_CASH, VAULT_POOL_LOCKED, or VAULT_POOL_BLOCKED)
    
    Returns:
        UUID: Account ID
    """
    # Validate account_type
    if account_type not in [
        AccountType.VAULT_POOL_CASH,  # AVAILABLE bucket (backward compatibility)
        AccountType.VAULT_POOL_LOCKED,
        AccountType.VAULT_POOL_BLOCKED,
    ]:
        raise ValueError(f"Invalid account_type for vault pool: {account_type}")
    
    # Find existing account
    account = db.query(Account).filter(
        Account.account_type == account_type,
        Account.vault_id == vault_id,
        Account.currency == currency,
        Account.user_id.is_(None),  # System account
        Account.offer_id.is_(None),  # Not an offer account
    ).first()
    
    if account:
        return account.id
    
    # Create new account
    account = Account(
        user_id=None,  # System account
        currency=currency,
        account_type=account_type,
        vault_id=vault_id,
        offer_id=None,
    )
    db.add(account)
    db.flush()  # Flush to get the ID
    
    return account.id


def ensure_vault_system_wallet(
    db: Session,
    vault_id: UUID,
    currency: str,
) -> Dict[str, UUID]:
    """
    Ensure all 3 buckets exist for a vault system wallet.
    
    Creates:
    - VAULT_POOL_CASH (AVAILABLE bucket, backward compatible)
    - VAULT_POOL_LOCKED
    - VAULT_POOL_BLOCKED
    
    Args:
        db: Database session
        vault_id: Vault UUID
        currency: Currency code (e.g., "AED")
    
    Returns:
        Dict mapping bucket names to account IDs:
        {
            "available": UUID,  # VAULT_POOL_CASH
            "locked": UUID,     # VAULT_POOL_LOCKED
            "blocked": UUID,    # VAULT_POOL_BLOCKED
        }
    """
    # Note: VAULT_POOL_CASH is the "available" bucket (backward compatibility)
    available_id = get_or_create_vault_pool_account(
        db, vault_id, currency, AccountType.VAULT_POOL_CASH
    )
    locked_id = get_or_create_vault_pool_account(
        db, vault_id, currency, AccountType.VAULT_POOL_LOCKED
    )
    blocked_id = get_or_create_vault_pool_account(
        db, vault_id, currency, AccountType.VAULT_POOL_BLOCKED
    )
    
    return {
        "available": available_id,
        "locked": locked_id,
        "blocked": blocked_id,
    }


def get_offer_system_wallet_balances(
    db: Session,
    offer_id: UUID,
    currency: str,
) -> Dict[str, Decimal]:
    """
    Get balances for all buckets of an offer system wallet.
    
    Args:
        db: Database session
        offer_id: Offer UUID
        currency: Currency code (e.g., "AED")
    
    Returns:
        Dict mapping bucket names to balances:
        {
            "available": Decimal,
            "locked": Decimal,
            "blocked": Decimal,
        }
    """
    wallet = ensure_offer_system_wallet(db, offer_id, currency)
    
    return {
        "available": get_account_balance(db, wallet["available"]),
        "locked": get_account_balance(db, wallet["locked"]),
        "blocked": get_account_balance(db, wallet["blocked"]),
    }


def get_vault_system_wallet_balances(
    db: Session,
    vault_id: UUID,
    currency: str,
) -> Dict[str, Decimal]:
    """
    Get balances for all buckets of a vault system wallet.
    
    Args:
        db: Database session
        vault_id: Vault UUID
        currency: Currency code (e.g., "AED")
    
    Returns:
        Dict mapping bucket names to balances:
        {
            "available": Decimal,  # From VAULT_POOL_CASH
            "locked": Decimal,     # From VAULT_POOL_LOCKED
            "blocked": Decimal,    # From VAULT_POOL_BLOCKED
        }
    """
    wallet = ensure_vault_system_wallet(db, vault_id, currency)
    
    return {
        "available": get_account_balance(db, wallet["available"]),
        "locked": get_account_balance(db, wallet["locked"]),
        "blocked": get_account_balance(db, wallet["blocked"]),
    }


