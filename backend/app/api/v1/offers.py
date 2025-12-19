"""
Client API - Offers (read-only listing + invest)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, List
from decimal import Decimal

from app.infrastructure.database import get_db
from app.core.offers.models import Offer, OfferStatus
from app.schemas.offers import OfferResponse, InvestInOfferRequest, OfferInvestmentResponse
from app.auth.dependencies import require_user_role
from app.auth.oidc import Principal
from app.services.offers.service import (
    invest_in_offer,
    OfferNotFoundError,
    OfferNotLiveError,
    OfferCurrencyMismatchError,
    OfferFullError,
)
from app.services.fund_services import InsufficientBalanceError

router = APIRouter()


@router.get(
    "/offers",
    response_model=List[OfferResponse],
    summary="List live offers",
    description="List offers with status LIVE. Only LIVE offers are visible to regular users. Requires USER role.",
)
async def list_offers(
    currency: Optional[str] = Query(None, description="Filter by currency (default: AED)"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> List[OfferResponse]:
    """List LIVE offers"""
    query = db.query(Offer).filter(Offer.status == OfferStatus.LIVE)
    
    if currency:
        query = query.filter(Offer.currency == currency)
    else:
        # Default to AED if no currency specified
        query = query.filter(Offer.currency == "AED")
    
    offers = query.order_by(Offer.created_at.desc()).limit(limit).offset(offset).all()
    
    return [
        OfferResponse(
            id=str(offer.id),
            code=offer.code,
            name=offer.name,
            description=offer.description,
            currency=offer.currency,
            max_amount=str(offer.max_amount),
            committed_amount=str(offer.committed_amount),
            remaining_amount=str(offer.max_amount - offer.committed_amount),
            maturity_date=offer.maturity_date.isoformat() if offer.maturity_date else None,
            status=offer.status.value,
            metadata=offer.offer_metadata,
            created_at=offer.created_at.isoformat(),
            updated_at=offer.updated_at.isoformat() if offer.updated_at else None,
        )
        for offer in offers
    ]


@router.get(
    "/offers/{offer_id}",
    response_model=OfferResponse,
    summary="Get offer details",
    description="Get detailed information about a specific LIVE offer. Requires USER role.",
)
async def get_offer(
    offer_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> OfferResponse:
    """Get LIVE offer by ID"""
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Only allow viewing LIVE offers for regular users
    if offer.status != OfferStatus.LIVE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    return OfferResponse(
        id=str(offer.id),
        code=offer.code,
        name=offer.name,
        description=offer.description,
        currency=offer.currency,
        max_amount=str(offer.max_amount),
        committed_amount=str(offer.committed_amount),
        remaining_amount=str(offer.max_amount - offer.committed_amount),
        maturity_date=offer.maturity_date.isoformat() if offer.maturity_date else None,
        status=offer.status.value,
        metadata=offer.offer_metadata,
        created_at=offer.created_at.isoformat(),
        updated_at=offer.updated_at.isoformat() if offer.updated_at else None,
    )


@router.post(
    "/offers/{offer_id}/invest",
    response_model=OfferInvestmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invest in an offer",
    description="Invest in a LIVE offer. Funds are moved from AVAILABLE to LOCKED. Partial fills are supported. Requires USER role.",
)
async def invest_in_offer_endpoint(
    offer_id: UUID,
    request: InvestInOfferRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> OfferInvestmentResponse:
    """Invest in an offer"""
    user_id = UUID(principal.sub)
    
    try:
        investment = invest_in_offer(
            db=db,
            user_id=user_id,
            offer_id=offer_id,
            amount=request.amount,
            currency=request.currency,
            idempotency_key=request.idempotency_key,
        )
        
        # Refresh offer to get updated committed_amount
        offer = db.query(Offer).filter(Offer.id == offer_id).first()
        
        return OfferInvestmentResponse(
            investment_id=str(investment.id),
            offer_id=str(investment.offer_id),
            requested_amount=str(investment.requested_amount),
            accepted_amount=str(investment.accepted_amount),
            currency=investment.currency,
            status=investment.status.value,
            offer_committed_amount=str(offer.committed_amount),
            offer_remaining_amount=str(offer.max_amount - offer.committed_amount),
            created_at=investment.created_at.isoformat(),
        )
    except OfferNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    except OfferNotLiveError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="OFFER_NOT_LIVE"
        )
    except OfferCurrencyMismatchError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="OFFER_CURRENCY_MISMATCH"
        )
    except OfferFullError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="OFFER_FULL"
        )
    except InsufficientBalanceError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="INSUFFICIENT_FUNDS"
        )
