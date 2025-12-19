"""
Admin API - Offers management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from uuid import UUID
from decimal import Decimal
from typing import Optional, List

from app.infrastructure.database import get_db
from app.core.offers.models import Offer, OfferStatus, InvestmentIntent, InvestmentIntentStatus
from app.core.users.models import User
from app.schemas.offers import CreateOfferRequest, UpdateOfferRequest, OfferResponse, OfferInvestmentListItem, OfferInvestmentsPaginatedResponse
from app.auth.dependencies import require_admin_role
from app.auth.oidc import Principal

router = APIRouter()


@router.post(
    "/offers",
    response_model=OfferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new offer",
    description="Create a new exclusive investment offer in DRAFT status. Requires ADMIN role.",
)
async def create_offer(
    request: CreateOfferRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> OfferResponse:
    """Create a new offer"""
    # Check if code already exists
    existing = db.query(Offer).filter(Offer.code == request.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="OFFER_CODE_EXISTS"
        )
    
    # Create offer
    offer = Offer(
        code=request.code,
        name=request.name,
        description=request.description,
        currency=request.currency,
        max_amount=request.max_amount,
        committed_amount=Decimal('0'),
        maturity_date=request.maturity_date,
        status=OfferStatus.DRAFT,
        offer_metadata=request.metadata,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    
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


@router.get(
    "/offers",
    response_model=List[OfferResponse],
    summary="List offers",
    description="List all offers with optional filters. Requires ADMIN role.",
)
async def list_offers(
    status_filter: Optional[OfferStatus] = Query(None, alias="status", description="Filter by status"),
    currency: Optional[str] = Query(None, description="Filter by currency"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> List[OfferResponse]:
    """List offers with filters"""
    query = db.query(Offer)
    
    if status_filter:
        query = query.filter(Offer.status == status_filter)
    if currency:
        query = query.filter(Offer.currency == currency)
    
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
    description="Get detailed information about a specific offer. Requires ADMIN role.",
)
async def get_offer(
    offer_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> OfferResponse:
    """Get offer by ID"""
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
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


@router.patch(
    "/offers/{offer_id}",
    response_model=OfferResponse,
    summary="Update offer",
    description="Update offer fields. Status transitions and max_amount changes are validated. Requires ADMIN role.",
)
async def update_offer(
    offer_id: UUID,
    request: UpdateOfferRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> OfferResponse:
    """Update offer"""
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Update fields
    if request.name is not None:
        offer.name = request.name
    if request.description is not None:
        offer.description = request.description
    if request.maturity_date is not None:
        offer.maturity_date = request.maturity_date
    if request.metadata is not None:
        offer.offer_metadata = request.metadata
    
    # Validate max_amount change
    if request.max_amount is not None:
        if request.max_amount < offer.committed_amount:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="INVALID_MAX_AMOUNT"
            )
        offer.max_amount = request.max_amount
    
    db.commit()
    db.refresh(offer)
    
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
    "/offers/{offer_id}/publish",
    response_model=OfferResponse,
    summary="Publish offer (DRAFT -> LIVE or PAUSED -> LIVE)",
    description="Change offer status from DRAFT to LIVE, or from PAUSED to LIVE. Requires ADMIN role.",
)
async def publish_offer(
    offer_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> OfferResponse:
    """Publish offer (DRAFT -> LIVE or PAUSED -> LIVE)"""
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    if offer.status not in [OfferStatus.DRAFT, OfferStatus.PAUSED]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="OFFER_CANNOT_BE_PUBLISHED"
        )
    
    offer.status = OfferStatus.LIVE
    db.commit()
    db.refresh(offer)
    
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
    "/offers/{offer_id}/pause",
    response_model=OfferResponse,
    summary="Pause offer (LIVE -> PAUSED)",
    description="Change offer status from LIVE to PAUSED. Requires ADMIN role.",
)
async def pause_offer(
    offer_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> OfferResponse:
    """Pause offer (LIVE -> PAUSED)"""
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    if offer.status != OfferStatus.LIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="OFFER_NOT_LIVE"
        )
    
    offer.status = OfferStatus.PAUSED
    db.commit()
    db.refresh(offer)
    
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
    "/offers/{offer_id}/close",
    response_model=OfferResponse,
    summary="Close offer (LIVE/PAUSED -> CLOSED)",
    description="Change offer status from LIVE or PAUSED to CLOSED. Requires ADMIN role.",
)
async def close_offer(
    offer_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> OfferResponse:
    """Close offer (LIVE/PAUSED -> CLOSED)"""
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    if offer.status not in [OfferStatus.LIVE, OfferStatus.PAUSED]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="OFFER_CANNOT_BE_CLOSED"
        )
    
    offer.status = OfferStatus.CLOSED
    db.commit()
    db.refresh(offer)
    
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


@router.get(
    "/offers/{offer_id}/investments",
    response_model=OfferInvestmentsPaginatedResponse,
    summary="List investments for an offer",
    description="List all investment intents for a specific offer with pagination. Requires ADMIN role.",
)
async def list_offer_investments(
    offer_id: UUID,
    status: Optional[str] = Query(None, alias="status", description="Filter by investment intent status: ALL, PENDING, CONFIRMED, REJECTED"),
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> OfferInvestmentsPaginatedResponse:
    """List investment intents for an offer with pagination"""
    # Verify offer exists
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Parse status filter (ALL means no filter)
    status_filter: Optional[InvestmentIntentStatus] = None
    if status and status.upper() != "ALL":
        try:
            status_filter = InvestmentIntentStatus[status.upper()]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status filter. Must be one of: ALL, PENDING, CONFIRMED, REJECTED"
            )
    
    # Base query for counting total
    count_query = db.query(InvestmentIntent).filter(InvestmentIntent.offer_id == offer_id)
    if status_filter:
        count_query = count_query.filter(InvestmentIntent.status == status_filter)
    total = count_query.count()
    
    # Query investment intents with user join
    query = db.query(
        InvestmentIntent,
        User.email
    ).join(
        User, InvestmentIntent.user_id == User.id
    ).filter(
        InvestmentIntent.offer_id == offer_id
    )
    
    if status_filter:
        query = query.filter(InvestmentIntent.status == status_filter)
    
    # Order by created_at DESC
    results = query.order_by(InvestmentIntent.created_at.desc()).limit(limit).offset(offset).all()
    
    items = [
        OfferInvestmentListItem(
            id=str(intent.id),
            offer_id=str(intent.offer_id),
            user_id=str(intent.user_id),
            user_email=user_email,
            requested_amount=str(intent.requested_amount),
            allocated_amount=str(intent.allocated_amount),
            currency=intent.currency,
            status=intent.status.value,
            created_at=intent.created_at.isoformat(),
            updated_at=intent.updated_at.isoformat() if intent.updated_at else None,
            idempotency_key=intent.idempotency_key,
        )
        for intent, user_email in results
    ]
    
    return OfferInvestmentsPaginatedResponse(
        items=items,
        limit=limit,
        offset=offset,
        total=total,
    )
