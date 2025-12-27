"""
Transactions API endpoints - READ-ONLY
"""

from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
import logging

from app.infrastructure.database import get_db
from app.core.transactions.models import Transaction, TransactionType, TransactionStatus
from app.core.ledger.models import LedgerEntryType
from app.core.ledger.models import LedgerEntry, Operation, OperationType, OperationStatus
from app.core.accounts.models import Account, AccountType
from app.core.offers.models import OfferInvestment, Offer
from app.core.users.models import User
from app.core.vaults.models import Vault
from app.schemas.wallet import TransactionListItem, TransactionDetailResponse, WalletMovement

from app.auth.dependencies import require_user_role, get_user_id_from_principal
from app.auth.oidc import Principal

router = APIRouter()
logger = logging.getLogger(__name__)


def _compute_operation_amount(
    db: Session,
    operation_id: UUID,
    user_id: UUID,
    currency: str,
) -> Decimal:
    """
    Compute operation amount by summing ledger entries affecting user wallet.
    
    Only includes ledger entries for user's wallet accounts (not INTERNAL_OMNIBUS).
    """
    # Get user's wallet account IDs for this currency
    wallet_accounts = db.query(Account).filter(
        Account.user_id == user_id,
        Account.currency == currency,
        Account.account_type.in_([
            AccountType.WALLET_AVAILABLE,
            AccountType.WALLET_BLOCKED,
            AccountType.WALLET_LOCKED,
        ])
    ).all()
    
    wallet_account_ids = [acc.id for acc in wallet_accounts]
    
    if not wallet_account_ids:
        return Decimal('0')
    
    # Sum ledger entries for user wallet accounts in this operation
    result = db.query(
        func.coalesce(func.sum(LedgerEntry.amount), Decimal('0'))
    ).filter(
        LedgerEntry.operation_id == operation_id,
        LedgerEntry.account_id.in_(wallet_account_ids),
    ).scalar()
    
    return Decimal(str(result)) if result is not None else Decimal('0')


def _compute_transaction_amount(
    db: Session,
    transaction_id: UUID,
    user_id: UUID,
    currency: str,
    transaction_type: Optional[TransactionType] = None,
    transaction_metadata: Optional[dict] = None,
) -> Decimal:
    """
    Compute transaction amount by summing ledger entries affecting user wallet.
    
    For INVESTMENT transactions, uses accepted_amount from metadata or absolute value of DEBIT.
    For other transactions, sums all ledger entries (net effect).
    
    Only includes ledger entries for user's wallet accounts (not INTERNAL_OMNIBUS).
    """
    # For INVESTMENT transactions, try to get amount from metadata first
    if transaction_type == TransactionType.INVESTMENT and transaction_metadata:
        if "accepted_amount" in transaction_metadata:
            try:
                return Decimal(str(transaction_metadata["accepted_amount"]))
            except (ValueError, TypeError):
                pass
    
    # Get user's wallet account IDs for this currency
    wallet_accounts = db.query(Account).filter(
        Account.user_id == user_id,
        Account.currency == currency,
        Account.account_type.in_([
            AccountType.WALLET_AVAILABLE,
            AccountType.WALLET_BLOCKED,
            AccountType.WALLET_LOCKED,
        ])
    ).all()
    
    wallet_account_ids = [acc.id for acc in wallet_accounts]
    
    if not wallet_account_ids:
        return Decimal('0')
    
    # Get all operations for this transaction
    operations = db.query(Operation).filter(
        Operation.transaction_id == transaction_id
    ).all()
    
    operation_ids = [op.id for op in operations]
    
    if not operation_ids:
        return Decimal('0')
    
    # For INVESTMENT transactions, use absolute value of DEBIT (amount moved from AVAILABLE)
    if transaction_type == TransactionType.INVESTMENT:
        debit_sum = db.query(
            func.coalesce(func.sum(func.abs(LedgerEntry.amount)), Decimal('0'))
        ).filter(
            LedgerEntry.operation_id.in_(operation_ids),
            LedgerEntry.account_id.in_(wallet_account_ids),
            LedgerEntry.entry_type == LedgerEntryType.DEBIT,
        ).scalar()
        if debit_sum and debit_sum > 0:
            return Decimal(str(debit_sum))
    
    # For other transactions, sum all ledger entries (net effect)
    result = db.query(
        func.coalesce(func.sum(LedgerEntry.amount), Decimal('0'))
    ).filter(
        LedgerEntry.operation_id.in_(operation_ids),
        LedgerEntry.account_id.in_(wallet_account_ids),
    ).scalar()
    
    return Decimal(str(result)) if result is not None else Decimal('0')


@router.get(
    "/transactions",
    response_model=List[TransactionListItem],
    summary="Get transaction history",
    description="Get transaction history for authenticated user. Includes Transactions and standalone Operations (e.g., INVEST_EXCLUSIVE). READ-ONLY endpoint. Requires USER role.",
)
async def get_transactions(
    currency: Optional[str] = Query(default=None, description="Filter by currency (e.g., AED)"),
    type: Optional[str] = Query(default=None, description="Filter by transaction type (DEPOSIT, WITHDRAWAL, INVESTMENT)"),
    status: Optional[str] = Query(default=None, description="Filter by transaction status"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of transactions to return"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> List[TransactionListItem]:
    """
    Get transaction history for authenticated user.
    
    Returns both:
    1. Transaction records (DEPOSIT, WITHDRAWAL, INVESTMENT)
    2. Standalone Operations that affect user wallet (e.g., INVEST_EXCLUSIVE from offers)
    
    Ordered by created_at DESC.
    
    Rules:
    - amount = sum of ledger entries affecting user wallet
    - Do NOT expose internal operations
    - Do NOT expose compliance reasons
    
    READ-ONLY: No side effects, no mutations.
    
    Requires authentication (Bearer token) with USER role.
    """
    user_id = get_user_id_from_principal(principal)
    
    # Get user's wallet account IDs for filtering operations
    wallet_accounts = db.query(Account).filter(
        Account.user_id == user_id,
        Account.account_type.in_([
            AccountType.WALLET_AVAILABLE,
            AccountType.WALLET_BLOCKED,
            AccountType.WALLET_LOCKED,
        ])
    ).all()
    wallet_account_ids = [acc.id for acc in wallet_accounts]
    
    # Build unified result list
    # DEFENSIVE: Wrap entire processing in try/except to ensure we always return valid JSON
    result = []
    
    try:
        # 1. Get Transactions
        txn_query = db.query(Transaction).filter(Transaction.user_id == user_id)
        
        if type:
            try:
                transaction_type = TransactionType[type.upper()]
                txn_query = txn_query.filter(Transaction.type == transaction_type)
            except KeyError:
                raise HTTPException(status_code=400, detail=f"Invalid transaction type: {type}")
        
        if status:
            try:
                transaction_status = TransactionStatus[status.upper()]
                txn_query = txn_query.filter(Transaction.status == transaction_status)
            except KeyError:
                raise HTTPException(status_code=400, detail=f"Invalid transaction status: {status}")
        
        transactions = txn_query.order_by(Transaction.created_at.desc()).limit(limit * 2).all()  # Get more to account for filtering
        
        for txn in transactions:
            try:
                # Determine currency: first try transaction metadata, then ledger entries, then default
                currency_val = "AED"  # Default
                try:
                    if txn.transaction_metadata and "currency" in txn.transaction_metadata:
                        currency_val = txn.transaction_metadata["currency"]
                    else:
                        # Fallback: get from first operation's ledger entry
                        operations = db.query(Operation).filter(Operation.transaction_id == txn.id).limit(1).all()
                        if operations:
                            ledger_entry = db.query(LedgerEntry).filter(
                                LedgerEntry.operation_id == operations[0].id
                            ).first()
                            if ledger_entry:
                                currency_val = ledger_entry.currency
                except (AttributeError, TypeError, KeyError):
                    # Keep default "AED"
                    pass
                
                # Filter by currency if specified
                if currency and currency_val != currency:
                    continue
                
                # Compute amount with error handling
                try:
                    amount = _compute_transaction_amount(
                        db, 
                        txn.id, 
                        user_id, 
                        currency_val,
                        transaction_type=txn.type,
                        transaction_metadata=txn.transaction_metadata,
                    )
                except Exception as e:
                    logger.warning(
                        f"Error computing amount for transaction {txn.id}: {e}",
                        extra={"transaction_id": str(txn.id)}
                    )
                    amount = Decimal('0')
                
                # Skip if amount is zero (no wallet impact)
                # Note: For INVESTMENT, amount should never be zero if transaction was successful
                if amount == 0:
                    continue
                
                # Get primary operation for metadata (defensive)
                try:
                    primary_op = db.query(Operation).filter(Operation.transaction_id == txn.id).first()
                    operation_type = primary_op.type.value if primary_op and primary_op.type else None
                except (AttributeError, TypeError):
                    primary_op = None
                    operation_type = None
                
                # Merge transaction metadata with operation metadata (transaction metadata takes precedence for offer info)
                try:
                    metadata = txn.transaction_metadata or {}
                    if primary_op and primary_op.operation_metadata:
                        # Merge operation metadata into transaction metadata
                        metadata = {**(primary_op.operation_metadata or {}), **metadata}
                except (AttributeError, TypeError):
                    metadata = {}
                
                # Extract offer_product for display (offer_name + offer_code) - defensive
                offer_product = None
                try:
                    if metadata:
                        offer_name = metadata.get("offer_name")
                        offer_code = metadata.get("offer_code")
                        if offer_name and offer_code:
                            offer_product = f"{offer_name} ({offer_code})"
                        elif offer_name:
                            offer_product = offer_name
                        elif offer_code:
                            offer_product = offer_code
                except (AttributeError, TypeError, KeyError):
                    offer_product = None
                
                # Normalize datetime (defensive)
                try:
                    if txn.created_at and txn.created_at.tzinfo is not None:
                        created_at_utc = txn.created_at.astimezone(timezone.utc)
                        iso_str = created_at_utc.isoformat()
                        if iso_str.endswith('+00:00') or iso_str.endswith('-00:00'):
                            created_at_str = iso_str[:-6] + 'Z'
                        elif '+' in iso_str or (iso_str.count('-') >= 3 and len(iso_str) > 19):
                            if len(iso_str) >= 6 and iso_str[-6] in '+-' and iso_str[-3] == ':':
                                created_at_str = iso_str[:-6] + 'Z'
                            else:
                                created_at_str = iso_str + 'Z'
                        else:
                            created_at_str = iso_str + 'Z'
                    elif txn.created_at:
                        created_at_str = txn.created_at.isoformat() + "Z"
                    else:
                        # Fallback: use current time
                        created_at_str = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                except (AttributeError, TypeError, ValueError):
                    # Fallback: use current time
                    created_at_str = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                
                # Calculate vault-specific fields (if primary_op is a vault operation)
                # DEFENSIVE: Always provide safe defaults to avoid serialization errors
                amount_display = None
                direction = None
                product_label = None
                
                try:
                    if primary_op and primary_op.type in [OperationType.VAULT_DEPOSIT, OperationType.VAULT_WITHDRAW_EXECUTED, OperationType.VAULT_VESTING_RELEASE]:
                        # Calculate amount_display (always positive) - defensive
                        try:
                            amount_display = str(abs(amount).quantize(Decimal('0.01')))
                        except (TypeError, ValueError, AttributeError):
                            # Fallback: use amount as string if quantize fails
                            try:
                                amount_display = str(abs(float(amount)))
                            except (TypeError, ValueError):
                                amount_display = "0.00"
                        
                        # Set direction based on operation type (defensive mapping)
                        if primary_op.type == OperationType.VAULT_DEPOSIT:
                            direction = "IN"
                        elif primary_op.type == OperationType.VAULT_WITHDRAW_EXECUTED:
                            direction = "OUT"
                        elif primary_op.type == OperationType.VAULT_VESTING_RELEASE:
                            direction = "IN"  # Release adds to available
                        else:
                            # Fallback: determine from amount sign
                            direction = "IN" if amount >= 0 else "OUT"
                        
                        # Get vault code from metadata or query Vault (defensive)
                        vault_code = None
                        try:
                            vault_code = metadata.get("vault_code") if metadata else None
                            if not vault_code and metadata and metadata.get("vault_id"):
                                try:
                                    vault_id = UUID(metadata["vault_id"])
                                    vault = db.query(Vault).filter(Vault.id == vault_id).first()
                                    if vault:
                                        vault_code = vault.code
                                except (ValueError, TypeError, AttributeError):
                                    pass
                        except (AttributeError, TypeError):
                            pass
                        
                        # For VAULT_VESTING_RELEASE, vault_code should always be 'AVENIR'
                        if primary_op.type == OperationType.VAULT_VESTING_RELEASE:
                            vault_code = vault_code or 'AVENIR'  # Fallback to AVENIR if missing
                        
                        # Set product_label with fallback
                        if vault_code:
                            product_label = f"COFFRE {vault_code}"
                        else:
                            product_label = "COFFRE"
                except Exception as e:
                    # Log but don't fail - use safe defaults
                    logger.warning(
                        f"Error computing vault fields for transaction {txn.id}: {e}",
                        extra={"transaction_id": str(txn.id), "operation_id": str(primary_op.id) if primary_op else None}
                    )
                    # Keep defaults (None) - schema allows None for these fields
                
                # Ensure offer_product has a fallback if missing
                if not offer_product and metadata:
                    try:
                        offer_name = metadata.get("offer_name") or "-"
                        offer_code = metadata.get("offer_code") or ""
                        if offer_code:
                            offer_product = f"{offer_name} ({offer_code})"
                        else:
                            offer_product = offer_name
                    except (AttributeError, TypeError):
                        offer_product = "-"
                
                try:
                    result.append(TransactionListItem(
                        transaction_id=str(txn.id),
                        operation_id=str(primary_op.id) if primary_op else None,
                        type=txn.type.value,
                        operation_type=operation_type,
                        status=txn.status.value,
                        amount=str(amount),
                        currency=currency_val,
                        created_at=created_at_str,
                        metadata=metadata,
                        offer_product=offer_product,
                        amount_display=amount_display,
                        direction=direction,
                        product_label=product_label,
                    ))
                except Exception as e:
                    # Log error but continue processing other transactions
                    logger.error(
                        f"Error serializing transaction {txn.id}: {e}",
                        extra={"transaction_id": str(txn.id), "error": str(e)},
                        exc_info=True
                    )
                    # Skip this transaction rather than failing the entire request
                    continue
            except Exception as e:
                # Log error but continue processing other transactions
                logger.error(
                    f"Error processing transaction {txn.id}: {e}",
                    extra={"transaction_id": str(txn.id), "error": str(e)},
                    exc_info=True
                )
                # Skip this transaction rather than failing the entire request
                continue
        
        # 2. Get standalone Operations (those without transaction_id) that affect user wallet
        if wallet_account_ids:
            op_query = db.query(Operation).filter(
            Operation.transaction_id.is_(None),
            Operation.type.in_([
                OperationType.INVEST_EXCLUSIVE,
                OperationType.VAULT_DEPOSIT,
                OperationType.VAULT_WITHDRAW_EXECUTED,
                OperationType.VAULT_VESTING_RELEASE,
            ]),  # User-facing standalone operations (offers + vaults)
        )
        
        # Filter by currency if specified
        if currency:
            # Get operations that have ledger entries in the specified currency
            op_ids_with_currency = db.query(LedgerEntry.operation_id).filter(
                LedgerEntry.account_id.in_(wallet_account_ids),
                LedgerEntry.currency == currency,
            ).distinct().all()
            op_ids_list = [op_id[0] for op_id in op_ids_with_currency]
            if op_ids_list:
                op_query = op_query.filter(Operation.id.in_(op_ids_list))
            else:
                standalone_ops = []
                op_query = None
        
        standalone_ops = op_query.order_by(Operation.created_at.desc()).limit(limit * 2).all() if op_query else []
        
        for op in standalone_ops:
            try:
                # Check if this operation affects user wallet
                ledger_entries = db.query(LedgerEntry).filter(
                    LedgerEntry.operation_id == op.id,
                    LedgerEntry.account_id.in_(wallet_account_ids),
                ).all()
                
                if not ledger_entries:
                    continue
                
                # Determine currency from ledger entry (defensive)
                try:
                    currency_val = ledger_entries[0].currency if ledger_entries else (currency or "AED")
                except (AttributeError, IndexError, TypeError):
                    currency_val = currency or "AED"
                
                # Filter by currency if specified
                if currency and currency_val != currency:
                    continue
                
                # Compute amount with error handling
                try:
                    amount = _compute_operation_amount(db, op.id, user_id, currency_val)
                except Exception as e:
                    logger.warning(
                        f"Error computing amount for operation {op.id}: {e}",
                        extra={"operation_id": str(op.id)}
                    )
                    amount = Decimal('0')
                
                # Skip if amount is zero
                if amount == 0:
                    continue
            
                # Get offer investment metadata if available (defensive)
                try:
                    metadata = op.operation_metadata or {}
                    offer_product = None
                    offer_investment = db.query(OfferInvestment).filter(OfferInvestment.operation_id == op.id).first()
                    if offer_investment:
                        offer = db.query(Offer).filter(Offer.id == offer_investment.offer_id).first()
                        if offer:
                            metadata = {
                                **(metadata or {}),
                                "offer_id": str(offer.id),
                                "offer_code": offer.code,
                                "offer_name": offer.name,
                                "investment_id": str(offer_investment.id),
                            }
                            offer_product = f"{offer.name} ({offer.code})"
                except (AttributeError, TypeError):
                    metadata = {}
                    offer_product = None
                
                # Normalize datetime (defensive)
                try:
                    if op.created_at and op.created_at.tzinfo is not None:
                        created_at_utc = op.created_at.astimezone(timezone.utc)
                        iso_str = created_at_utc.isoformat()
                        if iso_str.endswith('+00:00') or iso_str.endswith('-00:00'):
                            created_at_str = iso_str[:-6] + 'Z'
                        elif '+' in iso_str or (iso_str.count('-') >= 3 and len(iso_str) > 19):
                            if len(iso_str) >= 6 and iso_str[-6] in '+-' and iso_str[-3] == ':':
                                created_at_str = iso_str[:-6] + 'Z'
                            else:
                                created_at_str = iso_str + 'Z'
                        else:
                            created_at_str = iso_str + 'Z'
                    elif op.created_at:
                        created_at_str = op.created_at.isoformat() + "Z"
                    else:
                        # Fallback: use current time
                        created_at_str = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                except (AttributeError, TypeError, ValueError):
                    # Fallback: use current time
                    created_at_str = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                
                # Map operation type to transaction type for display (defensive)
                try:
                    display_type = "INVESTMENT" if op.type == OperationType.INVEST_EXCLUSIVE else (op.type.value if op.type else "UNKNOWN")
                except (AttributeError, TypeError):
                    display_type = "UNKNOWN"
                
                # Calculate vault-specific fields
                # DEFENSIVE: Always provide safe defaults to avoid serialization errors
                # This mapping is intentionally defensive to prevent UI errors when new OperationType are added
                amount_display = None
                direction = None
                product_label = None
                
                try:
                    if op.type in [OperationType.VAULT_DEPOSIT, OperationType.VAULT_WITHDRAW_EXECUTED, OperationType.VAULT_VESTING_RELEASE]:
                        # Calculate amount_display (always positive) - defensive
                        try:
                            amount_display = str(abs(amount).quantize(Decimal('0.01')))
                        except (TypeError, ValueError, AttributeError):
                            # Fallback: use amount as string if quantize fails
                            try:
                                amount_display = str(abs(float(amount)))
                            except (TypeError, ValueError):
                                amount_display = "0.00"
                        
                        # Set direction based on operation type (defensive mapping)
                        if op.type == OperationType.VAULT_DEPOSIT:
                            direction = "IN"
                        elif op.type == OperationType.VAULT_WITHDRAW_EXECUTED:
                            direction = "OUT"
                        elif op.type == OperationType.VAULT_VESTING_RELEASE:
                            direction = "IN"  # Release adds to available
                        else:
                            # Fallback: determine from amount sign
                            direction = "IN" if amount >= 0 else "OUT"
                        
                        # Get vault code from metadata or query Vault (defensive)
                        vault_code = None
                        try:
                            vault_code = metadata.get("vault_code") if metadata else None
                            if not vault_code and metadata and metadata.get("vault_id"):
                                try:
                                    vault_id = UUID(metadata["vault_id"])
                                    vault = db.query(Vault).filter(Vault.id == vault_id).first()
                                    if vault:
                                        vault_code = vault.code
                                except (ValueError, TypeError, AttributeError):
                                    pass
                        except (AttributeError, TypeError):
                            pass
                        
                        # For VAULT_VESTING_RELEASE, vault_code should always be 'AVENIR'
                        if op.type == OperationType.VAULT_VESTING_RELEASE:
                            vault_code = vault_code or 'AVENIR'  # Fallback to AVENIR if missing
                        
                        # Set product_label with fallback
                        if vault_code:
                            product_label = f"COFFRE {vault_code}"
                        else:
                            product_label = "COFFRE"
                except Exception as e:
                    # Log but don't fail - use safe defaults
                    logger.warning(
                        f"Error computing vault fields for operation {op.id}: {e}",
                        extra={"operation_id": str(op.id), "operation_type": op.type.value if op.type else None}
                    )
                    # Keep defaults (None) - schema allows None for these fields
                
                # Ensure offer_product has a fallback if missing (for INVEST_EXCLUSIVE)
                if not offer_product:
                    try:
                        if metadata:
                            offer_name = metadata.get("offer_name") or "-"
                            offer_code = metadata.get("offer_code") or ""
                            if offer_code:
                                offer_product = f"{offer_name} ({offer_code})"
                            else:
                                offer_product = offer_name
                        else:
                            offer_product = "-"
                    except (AttributeError, TypeError):
                        offer_product = "-"
                
                try:
                    result.append(TransactionListItem(
                        transaction_id=None,
                        operation_id=str(op.id),
                        type=display_type,
                        operation_type=op.type.value,
                        status=op.status.value,
                        amount=str(amount),
                        currency=currency_val,
                        created_at=created_at_str,
                        metadata=metadata,
                        offer_product=offer_product,
                        amount_display=amount_display,
                        direction=direction,
                        product_label=product_label,
                    ))
                except Exception as e:
                    # Log error but continue processing other operations
                    logger.error(
                        f"Error serializing operation {op.id}: {e}",
                        extra={"operation_id": str(op.id), "operation_type": op.type.value if op.type else None, "error": str(e)},
                        exc_info=True
                    )
                    # Skip this operation rather than failing the entire request
                    continue
            except Exception as e:
                # Log error but continue processing other operations
                logger.error(
                    f"Error processing operation {op.id}: {e}",
                    extra={"operation_id": str(op.id), "error": str(e)},
                    exc_info=True
                )
                # Skip this operation rather than failing the entire request
                continue
    
    except Exception as e:
        # Log critical error but return partial results rather than 500
        logger.error(
            f"Critical error in get_transactions for user {user_id}: {e}",
            extra={"user_id": str(user_id), "currency": currency, "error": str(e)},
            exc_info=True
        )
        # Return whatever we have so far (could be empty list, but valid JSON)
        # This prevents 500 errors from breaking the frontend
    
    # Sort by created_at DESC and limit
    try:
        result.sort(key=lambda x: x.created_at, reverse=True)
        return result[:limit]
    except Exception as e:
        # If sorting fails, return unsorted (better than 500)
        logger.warning(
            f"Error sorting transactions: {e}",
            extra={"error": str(e)}
        )
        return result[:limit]


def _infer_movement(transaction_type: TransactionType, status: TransactionStatus) -> WalletMovement | None:
    """
    Infer wallet movement (from bucket to bucket) based on transaction type and status.
    
    Rules:
    - DEPOSIT: UNDER_REVIEW -> AVAILABLE (if AVAILABLE) or -> COMPLIANCE_REVIEW (if COMPLIANCE_REVIEW)
    - INVESTMENT: AVAILABLE -> LOCKED
    - WITHDRAWAL: AVAILABLE -> (external, not shown)
    """
    if transaction_type == TransactionType.DEPOSIT:
        if status == TransactionStatus.AVAILABLE:
            return WalletMovement(from_bucket="UNDER_REVIEW", to_bucket="AVAILABLE")
        elif status == TransactionStatus.COMPLIANCE_REVIEW:
            return WalletMovement(from_bucket="UNDER_REVIEW", to_bucket="COMPLIANCE_REVIEW")
    elif transaction_type == TransactionType.INVESTMENT:
        if status == TransactionStatus.LOCKED:
            return WalletMovement(from_bucket="AVAILABLE", to_bucket="LOCKED")
    # WITHDRAWAL and other cases: return None
    return None


def _normalize_datetime(dt: datetime) -> str:
    """Normalize datetime to ISO 8601 string with Z suffix."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt_utc = dt.astimezone(timezone.utc)
        iso_str = dt_utc.isoformat()
        if iso_str.endswith('+00:00') or iso_str.endswith('-00:00'):
            return iso_str[:-6] + 'Z'
        elif '+' in iso_str or (iso_str.count('-') >= 3 and len(iso_str) > 19):
            if len(iso_str) >= 6 and iso_str[-6] in '+-' and iso_str[-3] == ':':
                return iso_str[:-6] + 'Z'
            else:
                return iso_str + 'Z'
        else:
            return iso_str + 'Z'
    else:
        return dt.isoformat() + "Z"


@router.get(
    "/transactions/{transaction_id}",
    response_model=TransactionDetailResponse,
    summary="Get transaction details",
    description="Get detailed information about a specific transaction. Requires USER role. User can only access their own transactions.",
)
async def get_transaction_detail(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> TransactionDetailResponse:
    """
    Get transaction details by ID.
    
    Returns 404 if transaction not found or not owned by user.
    """
    user_id = get_user_id_from_principal(principal)
    
    # Try to find transaction first
    txn = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id,
    ).first()
    
    if not txn:
        # Check if it's a standalone operation
        op = db.query(Operation).filter(
            Operation.id == transaction_id,
            Operation.transaction_id.is_(None),
        ).first()
        
        if not op:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Verify operation affects user wallet
        wallet_accounts = db.query(Account).filter(
            Account.user_id == user_id,
            Account.account_type.in_([
                AccountType.WALLET_AVAILABLE,
                AccountType.WALLET_BLOCKED,
                AccountType.WALLET_LOCKED,
            ])
        ).all()
        wallet_account_ids = [acc.id for acc in wallet_accounts]
        
        if wallet_account_ids:
            ledger_entries = db.query(LedgerEntry).filter(
                LedgerEntry.operation_id == op.id,
                LedgerEntry.account_id.in_(wallet_account_ids),
            ).first()
            
            if not ledger_entries:
                raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Build response from operation
        currency_val = "AED"  # Default
        if op.operation_metadata and "currency" in op.operation_metadata:
            currency_val = op.operation_metadata["currency"]
        else:
            ledger_entry = db.query(LedgerEntry).filter(
                LedgerEntry.operation_id == op.id
            ).first()
            if ledger_entry:
                currency_val = ledger_entry.currency
        
        amount = _compute_operation_amount(db, op.id, user_id, currency_val)
        
        # Get offer investment metadata if available
        metadata = op.operation_metadata or {}
        offer_investment = db.query(OfferInvestment).filter(OfferInvestment.operation_id == op.id).first()
        if offer_investment:
            offer = db.query(Offer).filter(Offer.id == offer_investment.offer_id).first()
            if offer:
                metadata = {
                    **(metadata or {}),
                    "offer_id": str(offer.id),
                    "offer_code": offer.code,
                    "offer_name": offer.name,
                    "investment_id": str(offer_investment.id),
                }
        
        # Get user email
        user = db.query(User).filter(User.id == user_id).first()
        user_email = user.email if user else None
        
        # Infer movement for INVEST_EXCLUSIVE
        movement = None
        if op.type == OperationType.INVEST_EXCLUSIVE:
            movement = WalletMovement(from_bucket="AVAILABLE", to_bucket="LOCKED")
        
        return TransactionDetailResponse(
            id=str(op.id),
            type="INVESTMENT" if op.type == OperationType.INVEST_EXCLUSIVE else op.type.value,
            status=op.status.value,
            amount=str(amount),
            currency=currency_val,
            created_at=_normalize_datetime(op.created_at),
            updated_at=_normalize_datetime(op.updated_at) if hasattr(op, 'updated_at') and op.updated_at else None,
            metadata=metadata,
            trace_id=op.operation_metadata.get("trace_id") if op.operation_metadata else None,
            user_email=user_email,
            operation_id=str(op.id),
            operation_type=op.type.value,
            movement=movement,
        )
    
    # Transaction found - build detailed response
    currency_val = "AED"  # Default
    if txn.transaction_metadata and "currency" in txn.transaction_metadata:
        currency_val = txn.transaction_metadata["currency"]
    else:
        operations = db.query(Operation).filter(Operation.transaction_id == txn.id).limit(1).all()
        if operations:
            ledger_entry = db.query(LedgerEntry).filter(
                LedgerEntry.operation_id == operations[0].id
            ).first()
            if ledger_entry:
                currency_val = ledger_entry.currency
    
    amount = _compute_transaction_amount(
        db,
        txn.id,
        user_id,
        currency_val,
        transaction_type=txn.type,
        transaction_metadata=txn.transaction_metadata,
    )
    
    # Get primary operation
    primary_op = db.query(Operation).filter(Operation.transaction_id == txn.id).first()
    
    # Merge metadata
    metadata = txn.transaction_metadata or {}
    if primary_op and primary_op.operation_metadata:
        metadata = {**(primary_op.operation_metadata or {}), **metadata}
    
    # Get user email
    user = db.query(User).filter(User.id == user_id).first()
    user_email = user.email if user else None
    
    # Infer movement
    movement = _infer_movement(txn.type, txn.status)
    
    # Get trace_id from metadata or operation
    trace_id = metadata.get("trace_id") if metadata else None
    if not trace_id and primary_op and primary_op.operation_metadata:
        trace_id = primary_op.operation_metadata.get("trace_id")
    
    return TransactionDetailResponse(
        id=str(txn.id),
        type=txn.type.value,
        status=txn.status.value,
        amount=str(amount),
        currency=currency_val,
        created_at=_normalize_datetime(txn.created_at),
        updated_at=_normalize_datetime(txn.updated_at) if hasattr(txn, 'updated_at') and txn.updated_at else None,
        metadata=metadata,
        trace_id=trace_id,
        user_email=user_email,
        operation_id=str(primary_op.id) if primary_op else None,
        operation_type=primary_op.type.value if primary_op else None,
        movement=movement,
    )
