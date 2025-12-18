"""
Compliance admin endpoints
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.infrastructure.database import get_db
from app.core.transactions.models import Transaction, TransactionType, TransactionStatus
from app.core.users.models import User
from app.schemas.compliance import DepositListItem
from app.auth.dependencies import require_admin_role, get_user_id_from_principal
from app.auth.oidc import Principal
from app.services.fund_services import release_compliance_funds, reject_deposit

router = APIRouter()


class ReleaseFundsRequest(BaseModel):
    """Release funds request schema"""
    transaction_id: str = Field(..., description="Transaction UUID")
    amount: str = Field(..., description="Amount to release")
    reason: str = Field(..., description="Reason for release")


class RejectDepositRequest(BaseModel):
    """Reject deposit request schema"""
    transaction_id: str = Field(..., description="Transaction UUID")
    reason: str = Field(..., description="Reason for rejection")


class ComplianceActionResponse(BaseModel):
    """Compliance action response schema"""
    transaction_id: str = Field(..., description="Transaction UUID")
    status: str = Field(..., description="Transaction status after action")


@router.get(
    "/compliance/deposits",
    response_model=List[DepositListItem],
    summary="List deposits for compliance review",
    description="List all DEPOSIT transactions for compliance review. Requires ADMIN role.",
)
async def list_deposits(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> List[DepositListItem]:
    """List deposits for compliance review"""
    transactions = (
        db.query(Transaction)
        .join(User, Transaction.user_id == User.id)
        .filter(Transaction.type == TransactionType.DEPOSIT)
        .order_by(Transaction.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    result = []
    for txn in transactions:
        user = db.query(User).filter(User.id == txn.user_id).first()
        # Extract amount from metadata if available
        amount = "0"
        currency = "AED"
        if txn.transaction_metadata:
            amount = str(txn.transaction_metadata.get("amount", "0"))
            currency = txn.transaction_metadata.get("currency", "AED")
        
        result.append(DepositListItem(
            transaction_id=str(txn.id),
            user_id=str(txn.user_id),
            email=user.email if user else "unknown",
            amount=amount,
            currency=currency,
            status=txn.status.value,
            created_at=txn.created_at.isoformat() + "Z",
            compliance_status=txn.status.value if txn.status.value in ["COMPLIANCE_REVIEW", "AVAILABLE"] else None,
        ))
    
    return result


@router.post(
    "/compliance/release-funds",
    response_model=ComplianceActionResponse,
    summary="Release funds from compliance review",
    description="Release funds from WALLET_BLOCKED to WALLET_AVAILABLE after compliance review. Requires ADMIN role.",
)
async def release_funds(
    request: ReleaseFundsRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> ComplianceActionResponse:
    """Release funds after compliance review"""
    try:
        transaction_id = UUID(request.transaction_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid transaction_id format"
        )
    
    # Get transaction
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    if transaction.type != TransactionType.DEPOSIT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction is not a deposit"
        )
    
    # Get actor user_id
    actor_user_id = get_user_id_from_principal(principal)
    
    # Release funds
    try:
        from decimal import Decimal
        operation = release_compliance_funds(
            db=db,
            user_id=transaction.user_id,
            transaction_id=transaction_id,
            amount=Decimal(request.amount),
            currency=transaction.transaction_metadata.get("currency", "AED") if transaction.transaction_metadata else "AED",
            actor_user_id=actor_user_id,
            reason=request.reason,
        )
        
        # Refresh transaction to get updated status
        db.refresh(transaction)
        
        return ComplianceActionResponse(
            transaction_id=str(transaction.id),
            status=transaction.status.value,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error releasing funds: {str(e)}"
        )


@router.post(
    "/compliance/reject-deposit",
    response_model=ComplianceActionResponse,
    summary="Reject deposit",
    description="Reject a deposit by reversing it. Requires ADMIN role.",
)
async def reject_deposit_endpoint(
    request: RejectDepositRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> ComplianceActionResponse:
    """Reject deposit"""
    try:
        transaction_id = UUID(request.transaction_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid transaction_id format"
        )
    
    # Get transaction
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    if transaction.type != TransactionType.DEPOSIT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction is not a deposit"
        )
    
    # Get actor user_id
    actor_user_id = get_user_id_from_principal(principal)
    
    # Reject deposit
    try:
        from decimal import Decimal
        # Extract amount and currency from transaction metadata
        amount = Decimal(transaction.transaction_metadata.get("amount", "0")) if transaction.transaction_metadata else Decimal("0")
        currency = transaction.transaction_metadata.get("currency", "AED") if transaction.transaction_metadata else "AED"
        
        operation = reject_deposit(
            db=db,
            transaction_id=transaction_id,
            user_id=transaction.user_id,
            currency=currency,
            amount=amount,
            actor_user_id=actor_user_id,
            reason=request.reason,
        )
        
        # Refresh transaction to get updated status
        db.refresh(transaction)
        
        return ComplianceActionResponse(
            transaction_id=str(transaction.id),
            status=transaction.status.value,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rejecting deposit: {str(e)}"
        )
