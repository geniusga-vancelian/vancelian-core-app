"""
Admin API - Vaults management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal
import logging

from app.infrastructure.database import get_db
from app.schemas.vaults import (
    AdminVaultsListResponse,
    AdminVaultRow,
    AdminPortfolioResponse,
    ProcessWithdrawalsResponse,
    WithdrawalListResponse,
    WithdrawalListItem,
    VaultSnapshot,
)
from app.auth.dependencies import require_admin_role
from app.auth.oidc import Principal
from app.services.vault_service import (
    get_vault_by_code,
    process_pending_withdrawals,
    VaultNotFoundError,
)
from app.services.vault_helpers import get_vault_cash_balance
from app.services.system_wallet_helpers import get_vault_system_wallet_balances
from app.core.vaults.models import Vault, WithdrawalRequest, WithdrawalRequestStatus, VaultAccount
from app.utils.trace_id import get_trace_id
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


class SystemWalletBalanceResponse(BaseModel):
    """System wallet balance response schema - shared between offers and vaults"""
    scope_type: str = Field(..., description="Scope type (VAULT or OFFER)")
    scope_id: str = Field(..., description="Scope ID (vault_id or offer_id)")
    currency: str = Field(..., description="Currency code")
    available: str = Field(..., description="Available balance")
    locked: str = Field(..., description="Locked balance")
    blocked: str = Field(..., description="Blocked balance")


@router.get(
    "/vaults",
    response_model=AdminVaultsListResponse,
    summary="List all vaults",
    description="List all vaults with pending withdrawal stats. Requires ADMIN role.",
)
async def list_vaults(
    http_request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> AdminVaultsListResponse:
    """List all vaults"""
    trace_id = get_trace_id(http_request) or "unknown"
    
    try:
        vaults = db.query(Vault).order_by(Vault.code).all()
        
        vault_rows = []
        for vault in vaults:
            # Count pending withdrawals
            pending_count = db.query(func.count(WithdrawalRequest.id)).filter(
                WithdrawalRequest.vault_id == vault.id,
                WithdrawalRequest.status == WithdrawalRequestStatus.PENDING,
            ).scalar() or 0
            
            # Sum pending amounts
            pending_amount_result = db.query(func.sum(WithdrawalRequest.amount)).filter(
                WithdrawalRequest.vault_id == vault.id,
                WithdrawalRequest.status == WithdrawalRequestStatus.PENDING,
            ).scalar()
            pending_amount = pending_amount_result if pending_amount_result else Decimal("0.00")
            
            # Get cash balance from ledger (source of truth)
            vault_cash_balance = get_vault_cash_balance(db, vault.id, "AED")  # TODO: support multi-currency
            
            # Get total_aum from sum of vault_accounts.principal
            total_aum_result = db.query(func.sum(VaultAccount.principal)).filter(
                VaultAccount.vault_id == vault.id,
            ).scalar()
            total_aum = Decimal(str(total_aum_result)) if total_aum_result else Decimal("0.00")
            
            vault_rows.append(
                AdminVaultRow(
                    id=str(vault.id),
                    code=vault.code,
                    name=vault.name,
                    status=vault.status.value,
                    cash_balance=str(vault_cash_balance),
                    total_aum=str(total_aum),
                    pending_withdrawals_count=pending_count,
                    pending_withdrawals_amount=str(pending_amount),
                    updated_at=vault.updated_at.isoformat() if vault.updated_at else None,
                )
            )
        
        return AdminVaultsListResponse(vaults=vault_rows)
    except Exception as e:
        logger.exception(
            f"Unexpected error in list_vaults: {type(e).__name__}: {str(e)}",
            extra={"trace_id": trace_id}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "trace_id": trace_id,
                }
            }
        )


@router.get(
    "/vaults/{vault_code}/portfolio",
    response_model=AdminPortfolioResponse,
    summary="Get vault portfolio",
    description="Get vault portfolio details including system wallet balances. Requires ADMIN role.",
)
async def get_vault_portfolio(
    vault_code: str,
    http_request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> AdminPortfolioResponse:
    """Get vault portfolio"""
    trace_id = get_trace_id(http_request) or "unknown"
    
    try:
        vault = get_vault_by_code(db, vault_code)
        
        # Count accounts
        accounts_count = db.query(func.count(VaultAccount.id)).filter(
            VaultAccount.vault_id == vault.id,
        ).scalar() or 0
        
        # Get system wallet balances (from ledger, source of truth)
        system_balances = get_vault_system_wallet_balances(db, vault.id, "AED")
        
        # Get cash balance from ledger (same as system_balances["available"])
        vault_cash_balance = get_vault_cash_balance(db, vault.id, "AED")
        
        # Get total_aum from sum of vault_accounts.principal
        total_aum_result = db.query(func.sum(VaultAccount.principal)).filter(
            VaultAccount.vault_id == vault.id,
        ).scalar()
        total_aum = Decimal(str(total_aum_result)) if total_aum_result else Decimal("0.00")
        
        # Count pending withdrawals
        pending_count = db.query(func.count(WithdrawalRequest.id)).filter(
            WithdrawalRequest.vault_id == vault.id,
            WithdrawalRequest.status == WithdrawalRequestStatus.PENDING,
        ).scalar() or 0
        
        vault_snapshot = VaultSnapshot(
            code=vault.code,
            name=vault.name,
            status=vault.status.value,
            cash_balance=str(vault_cash_balance),
            total_aum=str(total_aum),
        )
        
        return AdminPortfolioResponse(
            vault=vault_snapshot,
            accounts_count=accounts_count,
            system_wallet={
                "available": str(system_balances["available"]),
                "locked": str(system_balances["locked"]),
                "blocked": str(system_balances["blocked"]),
            },
            pending_withdrawals_count=pending_count,
        )
    except VaultNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "VAULT_NOT_FOUND",
                    "message": f"Vault '{vault_code}' not found",
                    "trace_id": trace_id,
                }
            }
        )
    except Exception as e:
        logger.exception(
            f"Unexpected error in get_vault_portfolio: {type(e).__name__}: {str(e)}",
            extra={"trace_id": trace_id, "vault_code": vault_code}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "trace_id": trace_id,
                }
            }
        )


@router.get(
    "/vaults/{vault_code}/withdrawals",
    response_model=WithdrawalListResponse,
    summary="List vault withdrawal requests",
    description="List withdrawal requests for a vault, optionally filtered by status. Requires ADMIN role.",
)
async def list_vault_withdrawals(
    vault_code: str,
    status_filter: str = Query(None, alias="status", description="Filter by status (PENDING, EXECUTED, CANCELLED)"),
    http_request: Request = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> WithdrawalListResponse:
    """List vault withdrawal requests"""
    trace_id = get_trace_id(http_request) or "unknown"
    
    try:
        vault = get_vault_by_code(db, vault_code)
        
        # Build query
        query = db.query(WithdrawalRequest).filter(
            WithdrawalRequest.vault_id == vault.id,
        )
        
        # Apply status filter if provided
        if status_filter:
            try:
                status_enum = WithdrawalRequestStatus[status_filter.upper()]
                query = query.filter(WithdrawalRequest.status == status_enum)
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": {
                            "code": "INVALID_STATUS",
                            "message": f"Invalid status: {status_filter}. Must be one of: PENDING, EXECUTED, CANCELLED",
                            "trace_id": trace_id,
                        }
                    }
                )
        
        # Order by created_at (FIFO order for PENDING)
        withdrawals = query.order_by(WithdrawalRequest.created_at).all()
        
        withdrawal_items = [
            WithdrawalListItem(
                request_id=str(w.id),
                amount=str(w.amount),
                currency="AED",  # TODO: support multi-currency
                status=w.status.value,
                reason=w.reason,
                created_at=w.created_at.isoformat(),
                executed_at=w.executed_at.isoformat() if w.executed_at else None,
            )
            for w in withdrawals
        ]
        
        return WithdrawalListResponse(withdrawals=withdrawal_items)
    except VaultNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "VAULT_NOT_FOUND",
                    "message": f"Vault '{vault_code}' not found",
                    "trace_id": trace_id,
                }
            }
        )
    except Exception as e:
        logger.exception(
            f"Unexpected error in list_vault_withdrawals: {type(e).__name__}: {str(e)}",
            extra={"trace_id": trace_id, "vault_code": vault_code}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "trace_id": trace_id,
                }
            }
        )


@router.post(
    "/vaults/{vault_code}/withdrawals/process",
    response_model=ProcessWithdrawalsResponse,
    summary="Process pending withdrawals (FIFO)",
    description="Process pending withdrawal requests in FIFO order. Requires ADMIN role.",
)
async def process_withdrawals_endpoint(
    vault_code: str,
    http_request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> ProcessWithdrawalsResponse:
    """Process pending withdrawals"""
    trace_id = get_trace_id(http_request) or "unknown"
    
    logger.info(
        f"Processing pending withdrawals: vault_code={vault_code}",
        extra={"trace_id": trace_id, "vault_code": vault_code}
    )
    
    try:
        result = process_pending_withdrawals(db=db, vault_code=vault_code)
        
        # Commit transaction
        db.commit()
        
        return ProcessWithdrawalsResponse(
            processed_count=result["processed_count"],
            remaining_count=result["remaining_count"],
        )
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(e),
                    "trace_id": trace_id,
                }
            }
        )
    except VaultNotFoundError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "VAULT_NOT_FOUND",
                    "message": f"Vault '{vault_code}' not found",
                    "trace_id": trace_id,
                }
            }
        )
    except Exception as e:
        db.rollback()
        logger.exception(
            f"Unexpected error in process_withdrawals_endpoint: {type(e).__name__}: {str(e)}",
            extra={"trace_id": trace_id, "vault_code": vault_code}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "trace_id": trace_id,
                }
            }
        )
