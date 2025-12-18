"""
Investment API endpoints - USER-facing (new implementation)

Endpoints:
- POST /api/v1/investments/subscribe
- POST /api/v1/investments/{investment_position_id}/redeem
- GET /api/v1/investments
"""

import logging
from uuid import UUID
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.investments_api import (
    SubscribeInvestmentRequest,
    SubscribeInvestmentResponse,
    RedeemInvestmentRequest,
    RedeemInvestmentResponse,
    InvestmentPositionListItem,
    ListInvestmentPositionsResponse,
)
from app.services.investments.service import (
    subscribe_investment,
    redeem_investment,
    InvestmentServiceError,
    InsufficientBalanceError,
    AccountNotFoundError,
    PositionNotFoundError,
    InvalidAmountError,
)
from app.auth.dependencies import require_user_role, get_user_id_from_principal
from app.auth.oidc import Principal
from app.core.investments.models import InvestmentPosition, InvestmentPositionStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/investments", tags=["investments"])


def handle_investment_error(error: Exception) -> HTTPException:
    """Convert investment service errors to HTTPException with standard error format"""
    if isinstance(error, InvalidAmountError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                'code': 'INVALID_AMOUNT',
                'message': str(error),
            }
        )
    elif isinstance(error, AccountNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                'code': 'ACCOUNT_NOT_FOUND',
                'message': str(error),
            }
        )
    elif isinstance(error, PositionNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                'code': 'POSITION_NOT_FOUND',
                'message': str(error),
            }
        )
    elif isinstance(error, InsufficientBalanceError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                'code': 'INSUFFICIENT_FUNDS',
                'message': str(error),
            }
        )
    else:
        logger.error(f"Unhandled investment service error: {error}", exc_info=True)
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                'code': 'INTERNAL_ERROR',
                'message': 'An internal error occurred',
            }
        )


@router.post(
    "/subscribe",
    response_model=SubscribeInvestmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subscribe to investment",
    description="Invest funds: Move from AVAILABLE to LOCKED. Creates or updates investment position.",
)
async def subscribe(
    request: SubscribeInvestmentRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> SubscribeInvestmentResponse:
    """
    Subscribe to an investment.
    
    Moves funds from AVAILABLE to LOCKED compartment and creates/updates investment position.
    
    Requires USER role.
    """
    user_id = get_user_id_from_principal(principal)
    
    try:
        amount = Decimal(request.amount)
    except (ValueError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                'code': 'INVALID_AMOUNT',
                'message': f"Invalid amount format: {request.amount}",
            }
        )
    
    try:
        result = subscribe_investment(
            db=db,
            user_id=user_id,
            currency=request.currency,
            product_code=request.product_code,
            amount=amount,
            idempotency_key=request.idempotency_key,
            metadata=request.metadata,
        )
        
        return SubscribeInvestmentResponse(
            investment_position_id=result['investment_position_id'],
            operation_id=result['operation_id'],
            transaction_id=result['transaction_id'],
            status=result['status'],
        )
    except InvestmentServiceError as e:
        raise handle_investment_error(e)
    except Exception as e:
        logger.error(f"Unexpected error in subscribe: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                'code': 'INTERNAL_ERROR',
                'message': 'An internal error occurred',
            }
        )


@router.post(
    "/{investment_position_id}/redeem",
    response_model=RedeemInvestmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Redeem investment",
    description="Redeem funds: Move from LOCKED to AVAILABLE. Decrements investment position.",
)
async def redeem(
    investment_position_id: UUID,
    request: RedeemInvestmentRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> RedeemInvestmentResponse:
    """
    Redeem from an investment.
    
    Moves funds from LOCKED to AVAILABLE compartment and decrements investment position.
    
    Requires USER role.
    """
    user_id = get_user_id_from_principal(principal)
    
    try:
        amount = Decimal(request.amount)
    except (ValueError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                'code': 'INVALID_AMOUNT',
                'message': f"Invalid amount format: {request.amount}",
            }
        )
    
    try:
        result = redeem_investment(
            db=db,
            user_id=user_id,
            investment_position_id=investment_position_id,
            amount=amount,
            idempotency_key=request.idempotency_key,
            metadata=request.metadata,
        )
        
        return RedeemInvestmentResponse(
            investment_position_id=result['investment_position_id'],
            operation_id=result['operation_id'],
            transaction_id=result['transaction_id'],
            position_status=result['position_status'],
            remaining_principal=result['remaining_principal'],
        )
    except InvestmentServiceError as e:
        raise handle_investment_error(e)
    except Exception as e:
        logger.error(f"Unexpected error in redeem: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                'code': 'INTERNAL_ERROR',
                'message': 'An internal error occurred',
            }
        )


@router.get(
    "/",
    response_model=ListInvestmentPositionsResponse,
    status_code=status.HTTP_200_OK,
    summary="List investment positions",
    description="List investment positions for the authenticated user.",
)
async def list_positions(
    currency: Optional[str] = Query(None, description="Filter by currency"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (ACTIVE, CLOSED)"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of results"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> ListInvestmentPositionsResponse:
    """
    List investment positions for the authenticated user.
    
    Requires USER role.
    """
    user_id = get_user_id_from_principal(principal)
    
    # Build query
    query = db.query(InvestmentPosition).filter(
        InvestmentPosition.user_id == user_id
    )
    
    if currency:
        query = query.filter(InvestmentPosition.currency == currency.upper())
    
    if status_filter:
        try:
            status_enum = InvestmentPositionStatus[status_filter.upper()]
            query = query.filter(InvestmentPosition.status == status_enum)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    'code': 'INVALID_STATUS',
                    'message': f"Invalid status: {status_filter}. Must be ACTIVE or CLOSED",
                }
            )
    
    # Order by created_at descending
    positions = query.order_by(InvestmentPosition.created_at.desc()).limit(limit or 100).all()
    
    # Convert to response
    items = [
        InvestmentPositionListItem(
            position_id=str(pos.id),
            currency=pos.currency,
            product_code=pos.product_code,
            status=pos.status.value,
            principal=str(pos.principal),
            created_at=pos.created_at.isoformat() if pos.created_at else "",
        )
        for pos in positions
    ]
    
    return ListInvestmentPositionsResponse(items=items)

