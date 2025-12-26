"""
DEV endpoints - Development-only debugging tools

These endpoints are only available when DEBUG mode is enabled or ENV is dev/local.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field

from app.infrastructure.database import get_db
from app.infrastructure.settings import get_settings
from app.auth.dependencies import require_user_role, get_user_id_from_principal
from app.auth.oidc import Principal
from app.services.wallet_helpers import get_wallet_balances
from app.services.system_wallet_helpers import (
    get_offer_system_wallet_balances,
    get_vault_system_wallet_balances,
)
from app.core.vaults.models import Vault, VaultAccount
from app.core.offers.models import Offer, OfferStatus
from app.core.accounts.wallet_locks import WalletLock, LockReason, LockStatus
from app.utils.trace_id import get_trace_id
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


def check_dev_mode() -> None:
    """Check if dev mode is enabled, raise 403 if not"""
    settings = get_settings()
    env_lower = settings.ENV.lower()
    is_dev_env = env_lower in ("dev", "local", "development")
    is_debug = settings.debug  # debug is a property
    
    if not (is_dev_env or is_debug):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "DEV_ENDPOINT_DISABLED",
                    "message": "This endpoint is only available in development mode.",
                    "trace_id": "dev-check",
                }
            }
        )


class ScopeInfo(BaseModel):
    """Scope information for a wallet row"""
    type: str = Field(..., description="Scope type: USER, VAULT, or OFFER")
    id: str | None = Field(None, description="Scope ID (vault_id or offer_id, null for USER)")
    owner: str = Field(..., description="Owner: USER or SYSTEM")


class WalletMatrixRow(BaseModel):
    """A single row in the wallet matrix"""
    label: str = Field(..., description="Human-readable label for this row")
    row_kind: str = Field(..., description="Row kind: USER_AED, OFFER_USER, VAULT_USER, OFFER_SYSTEM, VAULT_SYSTEM")
    scope: ScopeInfo = Field(..., description="Scope information")
    available: str = Field(..., description="Available balance")
    locked: str = Field(..., description="Locked balance")
    blocked: str = Field(..., description="Blocked balance")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    offer_id: str | None = Field(None, description="Offer ID if this row is for an offer")
    vault_id: str | None = Field(None, description="Vault ID if this row is for a vault")
    position_principal: str | None = Field(None, description="Principal position amount (for vaults or offers)")


class WalletMatrixResponse(BaseModel):
    """Wallet matrix response"""
    currency: str = Field(..., description="Currency code")
    columns: List[str] = Field(default=["available", "locked", "blocked"], description="Column names")
    rows: List[WalletMatrixRow] = Field(..., description="Wallet matrix rows")
    meta: Dict[str, Any] = Field(..., description="Metadata (generated_at, sim_version, etc.)")


@router.get(
    "/dev/wallet-matrix",
    response_model=WalletMatrixResponse,
    summary="Get wallet matrix (DEV ONLY)",
    description="Get a matrix view of wallet balances for user exposure only. DEV ONLY - requires DEBUG mode or dev/local environment.",
)
async def get_wallet_matrix(
    currency: str = Query("AED", description="Currency code (default: AED)"),
    show_system: bool = Query(False, description="Include system wallet rows (default: false)"),
    http_request: Request = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> WalletMatrixResponse:
    """
    Get wallet matrix showing all balances.
    
    DEV ONLY endpoint. Returns:
    - USER wallet balances (AVAILABLE/LOCKED/BLOCKED)
    - SYSTEM wallet balances for all vaults
    - SYSTEM wallet balances for all offers
    - USER position in vaults (if exists)
    """
    trace_id = get_trace_id(http_request) or "unknown"
    logger = logging.getLogger(__name__)  # Define logger early, before any try/except blocks
    
    # Validate currency parameter
    if not currency or not currency.strip():
        currency = "AED"  # Default to AED for DEV convenience
    currency = currency.strip().upper()
    
    # Validate currency format (basic check - only allow alphanumeric, 3-4 chars typical)
    if not currency.isalpha() or len(currency) < 3 or len(currency) > 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_CURRENCY",
                    "message": f"Invalid currency format: '{currency}'. Expected 3-4 letter currency code (e.g., AED, USD).",
                    "trace_id": trace_id,
                }
            }
        )
    
    # Check dev mode
    try:
        check_dev_mode()
    except HTTPException as e:
        e.detail["error"]["trace_id"] = trace_id
        raise
    
    try:
        user_id = get_user_id_from_principal(principal)
        logger.info(f"Wallet matrix request: user_id={user_id}, currency={currency}, trace_id={trace_id}")
    except Exception as e:
        logger.exception(f"Failed to get user_id from principal: {type(e).__name__}: {str(e)}", extra={"trace_id": trace_id})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_ERROR",
                    "message": "Failed to authenticate user",
                    "trace_id": trace_id,
                }
            }
        )
    
    rows: List[WalletMatrixRow] = []
    
    try:
        # Helper function to quantize Decimal to "0.00" format
        def quantize_amount(amount: Decimal) -> str:
            """Quantize Decimal to 2 decimal places and return as string"""
            return str(amount.quantize(Decimal('0.01')))
        
        # Row 1: AED (USER) - ALWAYS included
        # CANON RULE: locked MUST be 0 (locked/vested amounts are attributed to instruments, not AED row)
        # This is a business rule: even if WALLET_LOCKED has funds, we don't show them in AED row.
        # Instead, they are reclassified under the instrument (Offer/Vault) that locked them.
        user_balances = get_wallet_balances(db, user_id, currency)
        
        # INVARIANT: Force AED row locked to "0.00" regardless of WALLET_LOCKED balance
        # This ensures canonical display: locked amounts appear in instrument rows, not AED.
        aed_locked = Decimal("0.00")
        
        rows.append(WalletMatrixRow(
            label="AED (USER)",
            row_kind="USER_AED",
            scope=ScopeInfo(type="USER", id=None, owner="USER"),
            available=quantize_amount(user_balances["available_balance"]),
            locked=quantize_amount(aed_locked),  # ALWAYS 0.00 - canonical rule
            blocked=quantize_amount(user_balances["blocked_balance"]),
            meta={},
            offer_id=None,
            vault_id=None,
            position_principal=None,
        ))
        
        # Rows 2-N: USER VAULT positions (only if user has position: principal > 0)
        from app.core.vaults.models import VaultStatus
        vault_accounts = db.query(VaultAccount).join(Vault).filter(
            VaultAccount.user_id == user_id,
            VaultAccount.principal > Decimal("0.00"),
            Vault.status.in_([VaultStatus.ACTIVE, VaultStatus.PAUSED]),
        ).all()
        
        for vault_account in vault_accounts:
            vault = vault_account.vault
            position = vault_account.principal
            
            # Business mapping rules:
            # - VAULT FLEX: position goes to AVAILABLE column (from vault_account.principal)
            # - VAULT AVENIR: position goes to LOCKED column (from wallet_locks, source of truth)
            if vault.code.upper() == "FLEX":
                available = position
                locked = Decimal("0.00")
            elif vault.code.upper() == "AVENIR":
                # Source of truth: wallet_locks (reason=VAULT_AVENIR_VESTING, status=ACTIVE)
                vault_locked_total = db.query(
                    func.coalesce(func.sum(WalletLock.amount), Decimal("0.00"))
                ).filter(
                    WalletLock.user_id == user_id,
                    WalletLock.reference_type == "VAULT",
                    WalletLock.reference_id == vault.id,
                    WalletLock.reason == LockReason.VAULT_AVENIR_VESTING.value,
                    WalletLock.status == LockStatus.ACTIVE.value,
                    WalletLock.currency == currency,
                ).scalar()
                
                if vault_locked_total is None:
                    vault_locked_total = Decimal("0.00")
                else:
                    vault_locked_total = Decimal(str(vault_locked_total))
                
                # Fallback: if no wallet_locks exist yet (backward compat), use principal
                if vault_locked_total == Decimal("0.00") and position > Decimal("0.00"):
                    vault_locked_total = position
                
                available = Decimal("0.00")
                locked = vault_locked_total
            else:
                # Fallback: for other vaults, put in available for now
                available = position
                locked = Decimal("0.00")
            
            # MAPPING RULES ENFORCEMENT:
            # - FLEX: available only; locked + blocked = 0
            # - AVENIR: locked only; available + blocked = 0
            # Ensure blocked is always 0 for vaults
            blocked = Decimal("0.00")
            
            # Log if mapping rules are violated (but don't fail - display rules take precedence)
            if vault.code.upper() == "FLEX" and locked != Decimal("0.00"):
                logger.warning(
                    f"Wallet matrix: FLEX vault should have locked=0, got {locked}. Enforcing locked=0.",
                    extra={"vault_id": str(vault.id), "user_id": str(user_id), "trace_id": trace_id}
                )
                locked = Decimal("0.00")
            elif vault.code.upper() == "AVENIR" and available != Decimal("0.00"):
                logger.warning(
                    f"Wallet matrix: AVENIR vault should have available=0, got {available}. Enforcing available=0.",
                    extra={"vault_id": str(vault.id), "user_id": str(user_id), "trace_id": trace_id}
                )
                available = Decimal("0.00")
            
            rows.append(WalletMatrixRow(
                label=f"COFFRE — {vault.code}",
                row_kind="VAULT_USER",
                scope=ScopeInfo(type="VAULT", id=str(vault.id), owner="USER"),
                available=quantize_amount(available),
                locked=quantize_amount(locked),
                blocked=quantize_amount(blocked),  # Always 0 for vaults
                meta={"vault_code": vault.code},
                offer_id=None,
                vault_id=str(vault.id),
                position_principal=quantize_amount(position),  # Show position for reference
            ))
        
        # Optional: SYSTEM vault wallets (only if show_system=true)
        if show_system:
            vaults = db.query(Vault).filter(
                Vault.status.in_([VaultStatus.ACTIVE, VaultStatus.PAUSED])
            ).order_by(Vault.code).all()
            for vault in vaults:
                vault_balances = get_vault_system_wallet_balances(db, vault.id, currency)
                rows.append(WalletMatrixRow(
                    label=f"COFFRE — {vault.code} (SYSTEM)",
                    row_kind="VAULT_SYSTEM",
                    scope=ScopeInfo(type="VAULT", id=str(vault.id), owner="SYSTEM"),
                    available=quantize_amount(vault_balances["available"]),
                    locked=quantize_amount(vault_balances["locked"]),
                    blocked=quantize_amount(vault_balances["blocked"]),
                    meta={"vault_code": vault.code},
                    offer_id=None,
                    vault_id=str(vault.id),
                    position_principal=None,
                ))
        
        # Rows N+1-M: USER OFFER positions (only if user has invested)
        # SOURCE OF TRUTH: wallet_locks table (reason=OFFER_INVEST, status=ACTIVE)
        # ANTI-DOUBLE-COUNTING: These amounts are NOT added to AED row locked.
        # They are shown separately in OFFER_USER rows to provide instrument-level visibility.
        
        # Query wallet_locks for active OFFER_INVEST locks
        user_offer_locks_query = db.query(
            WalletLock.reference_id.label("offer_id"),
            func.sum(WalletLock.amount).label("total_invested")
        ).filter(
            WalletLock.user_id == user_id,
            WalletLock.reason == LockReason.OFFER_INVEST.value,
            WalletLock.reference_type == "OFFER",
            WalletLock.status == LockStatus.ACTIVE.value,
            WalletLock.currency == currency,
        ).group_by(WalletLock.reference_id).all()
        
        # Track total invested for validation (anti-double-counting check)
        total_offer_invested = Decimal("0.00")
        
        # Get offer details for user investments
        for offer_id, total_invested in user_offer_locks_query:
            total_offer_invested += total_invested
            offer = db.query(Offer).filter(Offer.id == offer_id).first()
            if offer:
                # Use offer.name if available, else fallback to offer.code
                offer_label = offer.name if offer.name else offer.code
                
                # MAPPING RULE ENFORCEMENT: Offer rows have locked only; available + blocked = 0
                offer_available = Decimal("0.00")
                offer_blocked = Decimal("0.00")
                offer_locked = total_invested
                
                rows.append(WalletMatrixRow(
                    label=f"OFFRE — {offer_label}",
                    row_kind="OFFER_USER",
                    scope=ScopeInfo(type="OFFER", id=str(offer.id), owner="USER"),
                    available=quantize_amount(offer_available),  # Always 0 for offers
                    locked=quantize_amount(offer_locked),  # User's investment position
                    blocked=quantize_amount(offer_blocked),  # Always 0 for offers
                    meta={
                        "offer_code": offer.code,
                        "offer_name": offer.name,
                    },
                    offer_id=str(offer.id),
                    vault_id=None,
                    position_principal=quantize_amount(total_invested),  # Show invested amount as principal
                ))
        
        # ANTI-DOUBLE-COUNTING VALIDATION (log only, don't fail)
        # If WALLET_LOCKED balance exists, it should match total_offer_invested + total_vault_locked
        # This is a sanity check to ensure we're not double-counting or missing amounts.
        # Note: This is informational only - we still enforce AED locked = 0.00 for display.
        if user_balances["locked_balance"] > Decimal("0.00"):
            total_vault_locked = sum(
                va.principal for va in vault_accounts 
                if va.vault.code.upper() == "AVENIR"
            )
            expected_locked = total_offer_invested + total_vault_locked
            # Log if there's a mismatch (but don't fail - display rules take precedence)
            if abs(user_balances["locked_balance"] - expected_locked) > Decimal("0.01"):
                logger.warning(
                    f"Wallet matrix: WALLET_LOCKED balance ({user_balances['locked_balance']}) "
                    f"does not match sum of investments ({total_offer_invested}) + AVENIR vaults ({total_vault_locked}). "
                    f"Display rule: AED locked = 0.00 (amounts shown in instrument rows).",
                    extra={"user_id": str(user_id), "trace_id": trace_id}
                )
        
        # Optional: SYSTEM offer wallets (only if show_system=true)
        if show_system:
            offers = db.query(Offer).filter(
                Offer.status.in_([OfferStatus.LIVE, OfferStatus.PAUSED])
            ).order_by(Offer.code).all()
            for offer in offers:
                offer_balances = get_offer_system_wallet_balances(db, offer.id, offer.currency)
                offer_label = offer.name if offer.name else offer.code
                rows.append(WalletMatrixRow(
                    label=f"OFFRE — {offer_label} (SYSTEM)",
                    row_kind="OFFER_SYSTEM",
                    scope=ScopeInfo(type="OFFER", id=str(offer.id), owner="SYSTEM"),
                    available=quantize_amount(offer_balances["available"]),
                    locked=quantize_amount(offer_balances["locked"]),
                    blocked=quantize_amount(offer_balances["blocked"]),
                    meta={"offer_code": offer.code, "offer_name": offer.name},
                    offer_id=str(offer.id),
                    vault_id=None,
                    position_principal=None,
                ))
        
        return WalletMatrixResponse(
            currency=currency,
            columns=["available", "locked", "blocked"],
            rows=rows,
            meta={
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sim_version": "v2",
                "user_id": str(user_id),
            },
        )
        
    except HTTPException:
        # Re-raise HTTPException as-is (already has proper JSON format)
        raise
    except Exception as e:
        # Log full traceback for debugging
        import traceback
        error_traceback = traceback.format_exc()
        logger.exception(
            f"Unexpected error in get_wallet_matrix: {type(e).__name__}: {str(e)}",
            extra={"trace_id": trace_id, "user_id": str(user_id) if 'user_id' in locals() else None}
        )
        logger.error(f"Full traceback:\n{error_traceback}", extra={"trace_id": trace_id})
        
        # Return structured JSON error (never raw stack trace)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Wallet matrix computation failed: {type(e).__name__}: {str(e)}",
                    "trace_id": trace_id,
                }
            }
        )

