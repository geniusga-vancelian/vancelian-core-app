#!/usr/bin/env python3
"""
Backfill script for AVENIR vesting lots

This script reconstructs vesting lots from historical AVENIR deposits.
It is idempotent: running it multiple times will not create duplicates.

Usage:
    python -m scripts.backfill_avenir_vesting_lots --dry-run
    python -m scripts.backfill_avenir_vesting_lots --currency AED
    python -m scripts.backfill_avenir_vesting_lots --user-id <uuid> --limit 100
"""

import argparse
import sys
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID
from typing import Optional

# Add backend to path
sys.path.insert(0, '.')

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.infrastructure.database import get_db
from app.core.ledger.models import Operation, OperationType, LedgerEntry, LedgerEntryType
from app.core.accounts.models import Account, AccountType
from app.core.vaults.models import VestingLot, VestingLotStatus, Vault
from app.core.accounts.wallet_locks import WalletLock, LockReason, LockStatus


def get_user_id_from_operation(db: Session, operation: Operation) -> Optional[UUID]:
    """
    Extract user_id from a VAULT_DEPOSIT operation.
    
    Strategy:
    1. Find the DEBIT ledger entry on WALLET_AVAILABLE (user's account)
    2. Get the Account associated with that entry
    3. Return the Account.user_id
    
    Returns None if user_id cannot be determined.
    """
    # Find DEBIT entry on WALLET_AVAILABLE
    debit_entry = db.query(LedgerEntry).join(Account).filter(
        LedgerEntry.operation_id == operation.id,
        LedgerEntry.entry_type == LedgerEntryType.DEBIT,
        Account.account_type == AccountType.WALLET_AVAILABLE,
    ).first()
    
    if not debit_entry:
        return None
    
    account = debit_entry.account
    return account.user_id


def get_deposit_amount_from_operation(db: Session, operation: Operation) -> Optional[Decimal]:
    """
    Extract deposit amount from a VAULT_DEPOSIT operation.
    
    Strategy:
    1. Find the DEBIT ledger entry on WALLET_AVAILABLE
    2. Return the absolute value of the amount (DEBIT is negative)
    
    Returns None if amount cannot be determined.
    """
    debit_entry = db.query(LedgerEntry).join(Account).filter(
        LedgerEntry.operation_id == operation.id,
        LedgerEntry.entry_type == LedgerEntryType.DEBIT,
        Account.account_type == AccountType.WALLET_AVAILABLE,
    ).first()
    
    if not debit_entry:
        return None
    
    # DEBIT entries are negative, so we take the absolute value
    return abs(Decimal(str(debit_entry.amount)))


def normalize_to_utc_midnight(dt) -> date:
    """Normalize a datetime to UTC midnight (date only)"""
    if hasattr(dt, 'date'):
        return dt.date()
    return dt


def backfill_avenir_vesting_lots(
    db: Session,
    currency: str = "AED",
    user_id: Optional[UUID] = None,
    limit: Optional[int] = None,
    dry_run: bool = False,
) -> dict:
    """
    Backfill vesting lots from historical AVENIR deposits.
    
    Source of truth:
    - Operations with type=VAULT_DEPOSIT
    - operation_metadata contains vault_code='AVENIR'
    - Ledger entries to extract user_id and amount
    
    Idempotence:
    - UNIQUE constraint on source_operation_id prevents duplicates
    - If lot already exists for an operation, skip it
    
    Returns:
        dict with statistics: created_count, skipped_count, errors
    """
    stats = {
        'created_count': 0,
        'skipped_count': 0,
        'errors': [],
    }
    
    # Query AVENIR deposit operations
    query = db.query(Operation).filter(
        Operation.type == OperationType.VAULT_DEPOSIT,
    )
    
    # Filter by vault_code='AVENIR' from metadata
    # Note: operation_metadata is JSON, so we need to check the JSON field
    # For SQLAlchemy with PostgreSQL JSON, we can use .astext or filter
    avenir_operations = []
    for op in query.all():
        metadata = op.operation_metadata or {}
        if metadata.get('vault_code') == 'AVENIR':
            # Also check currency if specified
            if currency and metadata.get('currency') != currency:
                continue
            avenir_operations.append(op)
    
    # Filter by user_id if specified
    if user_id:
        filtered_ops = []
        for op in avenir_operations:
            op_user_id = get_user_id_from_operation(db, op)
            if op_user_id == user_id:
                filtered_ops.append(op)
        avenir_operations = filtered_ops
    
    # Apply limit
    if limit:
        avenir_operations = avenir_operations[:limit]
    
    print(f"Found {len(avenir_operations)} AVENIR deposit operations to process")
    
    # Get AVENIR vault
    avenir_vault = db.query(Vault).filter(Vault.code == 'AVENIR').first()
    if not avenir_vault:
        stats['errors'].append("AVENIR vault not found in database")
        return stats
    
    # Process each operation
    for operation in avenir_operations:
        try:
            # Check if lot already exists (idempotence)
            existing_lot = db.query(VestingLot).filter(
                VestingLot.source_operation_id == operation.id
            ).first()
            
            if existing_lot:
                stats['skipped_count'] += 1
                continue
            
            # Extract user_id
            user_id_from_op = get_user_id_from_operation(db, operation)
            if not user_id_from_op:
                stats['errors'].append(f"Could not determine user_id for operation {operation.id}")
                continue
            
            # Extract amount
            amount = get_deposit_amount_from_operation(db, operation)
            if not amount or amount <= 0:
                stats['errors'].append(f"Invalid amount for operation {operation.id}")
                continue
            
            # Extract currency from metadata or ledger entry
            op_currency = (operation.operation_metadata or {}).get('currency', currency)
            
            # Calculate deposit_day and release_day
            deposit_day = normalize_to_utc_midnight(operation.created_at)
            release_day = deposit_day + timedelta(days=365)
            
            # Create vesting lot
            vesting_lot = VestingLot(
                vault_id=avenir_vault.id,
                vault_code='AVENIR',
                user_id=user_id_from_op,
                currency=op_currency,
                deposit_day=deposit_day,
                release_day=release_day,
                amount=amount,
                released_amount=Decimal('0.00'),
                status=VestingLotStatus.VESTED.value,
                source_operation_id=operation.id,
            )
            
            if not dry_run:
                db.add(vesting_lot)
                db.commit()
                stats['created_count'] += 1
                print(f"Created vesting lot for operation {operation.id} (user={user_id_from_op}, amount={amount}, deposit_day={deposit_day})")
            else:
                stats['created_count'] += 1
                print(f"[DRY RUN] Would create vesting lot for operation {operation.id} (user={user_id_from_op}, amount={amount}, deposit_day={deposit_day})")
        
        except Exception as e:
            db.rollback()
            error_msg = f"Error processing operation {operation.id}: {str(e)}"
            stats['errors'].append(error_msg)
            print(f"ERROR: {error_msg}")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='Backfill AVENIR vesting lots from historical deposits')
    parser.add_argument('--dry-run', action='store_true', help='Simulate without committing to database')
    parser.add_argument('--currency', default='AED', help='Currency filter (default: AED)')
    parser.add_argument('--user-id', type=str, help='Filter by user ID (UUID)')
    parser.add_argument('--limit', type=int, help='Limit number of operations to process')
    
    args = parser.parse_args()
    
    user_id_uuid = None
    if args.user_id:
        try:
            user_id_uuid = UUID(args.user_id)
        except ValueError:
            print(f"ERROR: Invalid user_id UUID: {args.user_id}")
            sys.exit(1)
    
    # Get database session
    db = next(get_db())
    
    try:
        print("=" * 80)
        print("AVENIR Vesting Lots Backfill")
        print("=" * 80)
        if args.dry_run:
            print("DRY RUN MODE - No changes will be committed")
        print(f"Currency: {args.currency}")
        if user_id_uuid:
            print(f"User ID filter: {user_id_uuid}")
        if args.limit:
            print(f"Limit: {args.limit}")
        print("=" * 80)
        
        stats = backfill_avenir_vesting_lots(
            db=db,
            currency=args.currency,
            user_id=user_id_uuid,
            limit=args.limit,
            dry_run=args.dry_run,
        )
        
        print("=" * 80)
        print("Backfill Summary")
        print("=" * 80)
        print(f"Created: {stats['created_count']}")
        print(f"Skipped (already exist): {stats['skipped_count']}")
        print(f"Errors: {len(stats['errors'])}")
        if stats['errors']:
            print("\nErrors:")
            for error in stats['errors']:
                print(f"  - {error}")
        print("=" * 80)
        
        if stats['errors']:
            sys.exit(1)
    
    finally:
        db.close()


if __name__ == '__main__':
    main()

