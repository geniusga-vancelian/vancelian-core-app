"""
Client API - Offers (read-only listing + invest)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session, selectinload, joinedload
from uuid import UUID
from typing import Optional, List
from decimal import Decimal
import logging

from app.infrastructure.database import get_db
from app.core.offers.models import Offer, OfferStatus, OfferMedia, OfferDocument, MediaVisibility, DocumentVisibility
from datetime import datetime, timezone
from app.schemas.offers import OfferResponse, InvestInOfferRequest, OfferInvestmentResponse, MediaItemResponse, DocumentItemResponse
from app.auth.dependencies import require_user_role
from app.auth.oidc import Principal
from app.utils.trace_id import get_trace_id
from app.infrastructure.settings import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)
from app.services.offers.service_v1_1 import (
    invest_in_offer_v1_1,
    OfferNotFoundError,
    OfferNotLiveError,
    OfferCurrencyMismatchError,
    OfferFullError,
    OfferClosedError,
    InsufficientAvailableFundsError,
)
from app.services.fund_services import InsufficientBalanceError, ValidationError

router = APIRouter()


def resolve_media_url(media: OfferMedia) -> Optional[str]:
    """Resolve media URL (public CDN or None for presigned)"""
    if media.url:
        return media.url
    if settings.S3_PUBLIC_BASE_URL:
        return f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{media.key}"
    return None


def resolve_document_url(doc: OfferDocument) -> Optional[str]:
    """Resolve document URL (public CDN or None for presigned)"""
    if doc.url:
        return doc.url
    if settings.S3_PUBLIC_BASE_URL:
        return f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{doc.key}"
    return None


def build_offer_response(offer: Offer, db: Session) -> OfferResponse:
    """Build OfferResponse with media and documents (PUBLIC only)
    
    Uses explicit queries to avoid SQLAlchemy relationship ambiguity.
    """
    # Get PUBLIC media via explicit query (avoid relationship ambiguity)
    media_list = db.query(OfferMedia).filter(
        OfferMedia.offer_id == offer.id,
        OfferMedia.visibility == MediaVisibility.PUBLIC
    ).order_by(OfferMedia.sort_order, OfferMedia.created_at).all()
    
    media_items = []
    for media in media_list:
        url = resolve_media_url(media)
        media_items.append(MediaItemResponse(
            id=str(media.id),
            type=media.type.value,
            url=url,
            mime_type=media.mime_type,
            size_bytes=media.size_bytes,
            sort_order=media.sort_order,
            is_cover=media.is_cover,
            created_at=media.created_at.isoformat(),
            width=media.width,
            height=media.height,
            duration_seconds=media.duration_seconds,
        ))
    
    # Get PUBLIC documents
    docs = db.query(OfferDocument).filter(
        OfferDocument.offer_id == offer.id,
        OfferDocument.visibility == DocumentVisibility.PUBLIC
    ).order_by(OfferDocument.created_at.desc()).all()
    
    doc_items = []
    for doc in docs:
        url = resolve_document_url(doc)
        doc_items.append(DocumentItemResponse(
            id=str(doc.id),
            name=doc.name,
            kind=doc.kind.value,
            url=url,
            mime_type=doc.mime_type,
            size_bytes=doc.size_bytes,
            created_at=doc.created_at.isoformat(),
        ))
    
    # Resolve cover URL if cover_media_id is set (explicit query, no relationship)
    cover_url = None
    if offer.cover_media_id:
        cover_media = db.query(OfferMedia).filter(
            OfferMedia.id == offer.cover_media_id,
            OfferMedia.visibility == MediaVisibility.PUBLIC
        ).first()
        if cover_media:
            cover_url = resolve_media_url(cover_media)
    
    # Compute fill percentage
    max_amount = float(offer.max_amount)
    committed_amount = float(offer.committed_amount or offer.invested_amount)
    fill_percentage = (committed_amount / max_amount * 100) if max_amount > 0 else 0.0
    
    # Compute days_left if maturity_date is set
    days_left = None
    if offer.maturity_date:
        now = datetime.now(timezone.utc)
        if offer.maturity_date.tzinfo is None:
            # If naive datetime, assume UTC
            maturity = offer.maturity_date.replace(tzinfo=timezone.utc)
        else:
            maturity = offer.maturity_date
        delta = maturity - now
        days_left = max(0, delta.days) if delta.total_seconds() > 0 else 0
    
    # Build marketing metrics with computed values
    marketing_metrics = None
    if offer.marketing_metrics:
        marketing_metrics = dict(offer.marketing_metrics)
        # Override days_left with computed value if not set
        if days_left is not None and 'days_left' not in marketing_metrics:
            marketing_metrics['days_left'] = days_left
    elif days_left is not None:
        marketing_metrics = {'days_left': days_left}
    
    return OfferResponse(
        id=str(offer.id),
        code=offer.code,
        name=offer.name,
        description=offer.description,
        currency=offer.currency,
        max_amount=str(offer.max_amount),
        committed_amount=str(offer.committed_amount or offer.invested_amount),
        remaining_amount=str(offer.remaining_amount if hasattr(offer, 'remaining_amount') else (offer.max_amount - (offer.invested_amount or offer.committed_amount))),
        maturity_date=offer.maturity_date.isoformat() if offer.maturity_date else None,
        status=offer.status.value,
        metadata=offer.offer_metadata,
        created_at=offer.created_at.isoformat(),
        updated_at=offer.updated_at.isoformat() if offer.updated_at else None,
        media=media_items,
        documents=doc_items,
        # Marketing V1.1 fields
        cover_media_id=str(offer.cover_media_id) if offer.cover_media_id else None,
        promo_video_media_id=str(offer.promo_video_media_id) if offer.promo_video_media_id else None,
        cover_url=cover_url,
        location_label=offer.location_label,
        location_lat=str(offer.location_lat) if offer.location_lat is not None else None,
        location_lng=str(offer.location_lng) if offer.location_lng is not None else None,
        marketing_title=offer.marketing_title,
        marketing_subtitle=offer.marketing_subtitle,
        marketing_why=offer.marketing_why if offer.marketing_why else None,
        marketing_highlights=offer.marketing_highlights if offer.marketing_highlights else None,
        marketing_breakdown=offer.marketing_breakdown if offer.marketing_breakdown else None,
        marketing_metrics=marketing_metrics,
        fill_percentage=round(fill_percentage, 2),
    )


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
    
    # No need to eager load offer_media - we use explicit queries in build_offer_response
    # This avoids SQLAlchemy relationship ambiguity issues
    
    offers = query.order_by(Offer.created_at.desc()).limit(limit).offset(offset).all()
    
    return [build_offer_response(offer, db) for offer in offers]


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
    # No need to eager load offer_media - we use explicit queries in build_offer_response
    # This avoids SQLAlchemy relationship ambiguity issues
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
    
    return build_offer_response(offer, db)


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
    http_request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> OfferInvestmentResponse:
    """Invest in an offer"""
    trace_id = get_trace_id(http_request) or "unknown"
    user_id = UUID(principal.sub)
    
    logger.info(
        f"Investment request: offer_id={offer_id}, user_id={user_id}, amount={request.amount}, currency={request.currency}",
        extra={"trace_id": trace_id, "offer_id": str(offer_id), "user_id": str(user_id)}
    )
    
    try:
        intent, remaining_after = invest_in_offer_v1_1(
            db=db,
            user_id=user_id,
            offer_id=offer_id,
            amount=request.amount,
            currency=request.currency,
            idempotency_key=request.idempotency_key,
        )
        
        # Commit transaction (all writes are atomic)
        db.commit()
        
        # Refresh offer to get updated invested_amount
        offer = db.query(Offer).filter(Offer.id == offer_id).first()
        
        return OfferInvestmentResponse(
            investment_id=str(intent.id),
            offer_id=str(intent.offer_id),
            requested_amount=str(intent.requested_amount),
            accepted_amount=str(intent.allocated_amount),  # v1.1 uses allocated_amount
            currency=intent.currency,
            status=intent.status.value,  # PENDING, CONFIRMED, REJECTED
            offer_committed_amount=str(offer.invested_amount or offer.committed_amount),
            offer_remaining_amount=str(remaining_after),
            created_at=intent.created_at.isoformat(),
        )
    except ValidationError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except OfferNotFoundError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    except OfferClosedError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="OFFER_CLOSED"
        )
    except OfferNotLiveError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="OFFER_NOT_LIVE"
        )
    except OfferCurrencyMismatchError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="OFFER_CURRENCY_MISMATCH"
        )
    except OfferFullError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="OFFER_FULL"
        )
    except InsufficientAvailableFundsError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="INSUFFICIENT_AVAILABLE_FUNDS"
        )
    except InsufficientBalanceError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="INSUFFICIENT_AVAILABLE_FUNDS"
        )
    except Exception as e:
        db.rollback()
        logger.exception(
            f"Unexpected error in invest_in_offer_endpoint: {type(e).__name__}: {str(e)}",
            extra={"trace_id": trace_id, "offer_id": str(offer_id), "user_id": str(user_id), "error_type": type(e).__name__}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_ERROR",
                "trace_id": trace_id,
                "message": "An unexpected error occurred"
            }
        )
