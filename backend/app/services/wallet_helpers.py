"""
Wallet account provisioning and balance helpers
"""

from decimal import Decimal
from typing import Dict
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from app.core.accounts.models import Account, AccountType
from app.core.ledger.models import LedgerEntry


def ensure_wallet_accounts(db: Session, user_id: UUID, currency: str) -> Dict[str, UUID]:
    """
    Ensure wallet accounts exist for a user and currency.
    
    Creates missing accounts for:
    - WALLET_AVAILABLE
    - WALLET_BLOCKED
    - WALLET_LOCKED
    
    Returns a dict mapping account_type to account_id.
    """
    required_types = [
        AccountType.WALLET_AVAILABLE,
        AccountType.WALLET_BLOCKED,
        AccountType.WALLET_LOCKED,
    ]
    
    result = {}
    
    for account_type in required_types:
        # Check if account exists
        account = db.query(Account).filter(
            Account.user_id == user_id,
            Account.currency == currency,
            Account.account_type == account_type,
        ).first()
        
        if account:
            result[account_type.value] = account.id
        else:
            # Create missing account
            account = Account(
                user_id=user_id,
                currency=currency,
                account_type=account_type,
            )
            db.add(account)
            db.flush()  # Flush to get the ID
            result[account_type.value] = account.id
    
    return result


def get_account_balance(db: Session, account_id: UUID) -> Decimal:
    """
    Get account balance by summing all ledger entries.
    
    Returns Decimal(0) if no entries exist.
    """
    result = db.query(
        func.coalesce(func.sum(LedgerEntry.amount), Decimal('0'))
    ).filter(
        LedgerEntry.account_id == account_id
    ).scalar()
    
    return Decimal(str(result)) if result is not None else Decimal('0')


def get_wallet_balances(db: Session, user_id: UUID, currency: str) -> Dict[str, Decimal]:
    """
    Get wallet balances for all compartments.
    
    Returns:
    - total_balance: Sum of all wallet accounts
    - available_balance: WALLET_AVAILABLE balance
    - blocked_balance: WALLET_BLOCKED balance
    - locked_balance: WALLET_LOCKED balance
    """
    # Get account IDs for wallet compartments
    accounts = db.query(Account).filter(
        Account.user_id == user_id,
        Account.currency == currency,
        Account.account_type.in_([
            AccountType.WALLET_AVAILABLE,
            AccountType.WALLET_BLOCKED,
            AccountType.WALLET_LOCKED,
        ])
    ).all()
    
    # Map account_type to account_id
    account_map = {acc.account_type: acc.id for acc in accounts}
    
    # Calculate balances
    available_balance = get_account_balance(
        db, account_map.get(AccountType.WALLET_AVAILABLE)
    ) if AccountType.WALLET_AVAILABLE in account_map else Decimal('0')
    
    blocked_balance = get_account_balance(
        db, account_map.get(AccountType.WALLET_BLOCKED)
    ) if AccountType.WALLET_BLOCKED in account_map else Decimal('0')
    
    locked_balance = get_account_balance(
        db, account_map.get(AccountType.WALLET_LOCKED)
    ) if AccountType.WALLET_LOCKED in account_map else Decimal('0')
    
    total_balance = available_balance + blocked_balance + locked_balance
    
    return {
        'total_balance': total_balance,
        'available_balance': available_balance,
        'blocked_balance': blocked_balance,
        'locked_balance': locked_balance,
    }


