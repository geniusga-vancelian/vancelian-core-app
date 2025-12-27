"""
Client API - Vaults (deposits and withdrawals)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from uuid import UUID
from decimal import Decimal
import logging

from app.infrastructure.database import get_db
from app.schemas.vaults import (
    VaultAccountMeResponse,
    DepositRequest,
    DepositResponse,
    WithdrawRequest,
    WithdrawResponse,
    WithdrawalListResponse,
    WithdrawalListItem,
)
from app.auth.dependencies import require_user_role, get_user_id_from_principal
from app.auth.oidc import Principal
from app.services.vault_service import (
    get_vault_by_code,
    get_or_create_vault_account,
    deposit_to_vault,
    request_withdrawal,
    VaultNotFoundError,
    VaultPausedError,
    VaultLockedError,
    InsufficientUserBalanceError,
    InsufficientVaultBalanceError,
)
from app.services.vault_helpers import get_vault_cash_balance
from app.core.vaults.models import WithdrawalRequest, WithdrawalRequestStatus
from app.utils.trace_id import get_trace_id
from app.schemas.vaults import VestingTimelineResponse, VestingTimelineItem
from app.core.vaults.models import VestingLot, VestingLotStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/vaults/{vault_code}/me",
    response_model=VaultAccountMeResponse,
    summary="Get my vault account",
    description="Get authenticated user's account in a vault. Requires USER role.",
)
async def get_vault_account_me(
    vault_code: str,
    http_request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> VaultAccountMeResponse:
    """Get user's vault account"""
    trace_id = get_trace_id(http_request) or "unknown"
    user_id = get_user_id_from_principal(principal)
    
    try:
        vault = get_vault_by_code(db, vault_code)
        vault_account = get_or_create_vault_account(db, vault.id, user_id)
        
        # Get vault cash balance from ledger
        vault_cash_balance = get_vault_cash_balance(db, vault.id, "AED")
        
        # Build vault snapshot
        vault_snapshot = {
            "code": vault.code,
            "name": vault.name,
            "status": vault.status.value,
            "cash_balance": str(vault_cash_balance),
            "total_aum": str(vault.total_aum),
        }
        
        return VaultAccountMeResponse(
            vault_account_id=str(vault_account.id),
            principal=str(vault_account.principal),
            available_balance=str(vault_account.available_balance),
            locked_until=vault_account.locked_until.isoformat() if vault_account.locked_until else None,
            vault=vault_snapshot,
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
            f"Unexpected error in get_vault_account_me: {type(e).__name__}: {str(e)}",
            extra={"trace_id": trace_id, "vault_code": vault_code, "user_id": str(user_id)}
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
    "/vaults/{vault_code}/deposits",
    response_model=DepositResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Deposit to vault",
    description="Deposit funds from wallet to vault. Requires USER role.",
)
async def deposit_to_vault_endpoint(
    vault_code: str,
    request: DepositRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> DepositResponse:
    """Deposit funds to vault"""
    trace_id = get_trace_id(http_request) or "unknown"
    user_id = get_user_id_from_principal(principal)
    
    logger.info(
        f"Vault deposit request: vault_code={vault_code}, user_id={user_id}, amount={request.amount}, currency={request.currency}",
        extra={"trace_id": trace_id, "vault_code": vault_code, "user_id": str(user_id)}
    )
    
    try:
        result = deposit_to_vault(
            db=db,
            user_id=user_id,
            vault_code=vault_code,
            amount=request.amount,
            currency=request.currency,
        )
        
        # Commit transaction
        db.commit()
        
        return DepositResponse(
            operation_id=result["operation_id"],
            vault_account_id=result["vault_account_id"],
            vault=result["vault_snapshot"],
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
    except VaultPausedError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "VAULT_PAUSED",
                    "message": str(e),
                    "trace_id": trace_id,
                }
            }
        )
    except InsufficientUserBalanceError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "INSUFFICIENT_BALANCE",
                    "message": str(e),
                    "trace_id": trace_id,
                }
            }
        )
    except Exception as e:
        db.rollback()
        import traceback
        error_details = traceback.format_exc()
        logger.exception(
            f"Unexpected error in deposit_to_vault_endpoint: {type(e).__name__}: {str(e)}",
            extra={"trace_id": trace_id, "vault_code": vault_code, "user_id": str(user_id)}
        )
        logger.error(f"Full traceback: {error_details}", extra={"trace_id": trace_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"An unexpected error occurred: {type(e).__name__}: {str(e)}",
                    "trace_id": trace_id,
                }
            }
        )


@router.post(
    "/vaults/{vault_code}/withdrawals",
    response_model=WithdrawResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request withdrawal from vault",
    description="Request withdrawal from vault. Executes immediately if vault has sufficient cash, otherwise queues as PENDING. Requires USER role.",
)
async def request_withdrawal_endpoint(
    vault_code: str,
    request: WithdrawRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> WithdrawResponse:
    """Request withdrawal from vault"""
    trace_id = get_trace_id(http_request) or "unknown"
    user_id = get_user_id_from_principal(principal)
    
    logger.info(
        f"Vault withdrawal request: vault_code={vault_code}, user_id={user_id}, amount={request.amount}, currency={request.currency}",
        extra={"trace_id": trace_id, "vault_code": vault_code, "user_id": str(user_id)}
    )
    
    try:
        result = request_withdrawal(
            db=db,
            user_id=user_id,
            vault_code=vault_code,
            amount=request.amount,
            currency=request.currency,
            reason=request.reason,
        )
        
        # Commit transaction
        db.commit()
        
        return WithdrawResponse(
            request_id=result["request_id"],
            status=result["status"],
            operation_id=result.get("operation_id"),
            vault=result["vault_snapshot"],
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
    except VaultPausedError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "VAULT_PAUSED",
                    "message": str(e),
                    "trace_id": trace_id,
                }
            }
        )
    except VaultLockedError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "VAULT_LOCKED",
                    "message": str(e),
                    "trace_id": trace_id,
                }
            }
        )
    except InsufficientUserBalanceError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "INSUFFICIENT_BALANCE",
                    "message": str(e),
                    "trace_id": trace_id,
                }
            }
        )
    except Exception as e:
        db.rollback()
        logger.exception(
            f"Unexpected error in request_withdrawal_endpoint: {type(e).__name__}: {str(e)}",
            extra={"trace_id": trace_id, "vault_code": vault_code, "user_id": str(user_id)}
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
    summary="List my withdrawal requests",
    description="List authenticated user's withdrawal requests for a vault. Requires USER role.",
)
async def list_my_withdrawals(
    vault_code: str,
    http_request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> WithdrawalListResponse:
    """List user's withdrawal requests"""
    trace_id = get_trace_id(http_request) or "unknown"
    user_id = get_user_id_from_principal(principal)
    
    try:
        vault = get_vault_by_code(db, vault_code)
        
        # Get user's withdrawal requests
        withdrawals = db.query(WithdrawalRequest).filter(
            WithdrawalRequest.vault_id == vault.id,
            WithdrawalRequest.user_id == user_id,
        ).order_by(WithdrawalRequest.created_at.desc()).all()
        
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
            f"Unexpected error in list_my_withdrawals: {type(e).__name__}: {str(e)}",
            extra={"trace_id": trace_id, "vault_code": vault_code, "user_id": str(user_id)}
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
