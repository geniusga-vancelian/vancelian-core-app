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
from app.schemas.offers import (
    OfferResponse, InvestInOfferRequest, OfferInvestmentResponse, MediaItemResponse, DocumentItemResponse,
    OfferMediaBlockResponse, PresignedMediaItemResponse, PresignedDocumentItemResponse
)
from app.auth.dependencies import require_user_role
from app.auth.oidc import Principal
from app.core.articles.models import Article, ArticleMedia, ArticleStatus
from app.schemas.articles import ArticlePublicListItem
from app.core.offers.models import OfferTimelineEvent
from app.schemas.offers_timeline import TimelineEventResponse, TimelineEventArticleInfo
from app.utils.trace_id import get_trace_id
from app.infrastructure.settings import get_settings
from app.services.storage.s3_service import get_s3_service
from app.services.storage.exceptions import StorageNotConfiguredError

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


def generate_presigned_url_for_media(media: OfferMedia) -> Optional[str]:
    """
    Generate presigned URL for media.
    Returns None if storage is not configured or if media.url exists (public CDN).
    """
    # If media has a public URL, prefer it
    if media.url:
        return media.url
    
    # Try to generate presigned URL
    try:
        s3_service = get_s3_service()
        return s3_service.generate_presigned_get_url(key=media.key)
    except StorageNotConfiguredError:
        # Storage not configured - return None
        logger.warning(f"Storage not configured, cannot generate presigned URL for media {media.id}")
        return None
    except Exception as e:
        logger.error(f"Failed to generate presigned URL for media {media.id}: {str(e)}")
        return None


def generate_presigned_url_for_document(doc: OfferDocument) -> Optional[str]:
    """
    Generate presigned URL for document.
    Returns None if storage is not configured or if doc.url exists (public CDN).
    """
    # If document has a public URL, prefer it
    if doc.url:
        return doc.url
    
    # Try to generate presigned URL
    try:
        s3_service = get_s3_service()
        return s3_service.generate_presigned_get_url(key=doc.key)
    except StorageNotConfiguredError:
        # Storage not configured - return None
        logger.warning(f"Storage not configured, cannot generate presigned URL for document {doc.id}")
        return None
    except Exception as e:
        logger.error(f"Failed to generate presigned URL for document {doc.id}: {str(e)}")
        return None


def resolve_media_url(media: OfferMedia) -> Optional[str]:
    """Resolve media URL (public CDN or None for presigned) - DEPRECATED: use generate_presigned_url_for_media"""
    if media.url:
        return media.url
    if settings.S3_PUBLIC_BASE_URL:
        return f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{media.key}"
    return None


def resolve_document_url(doc: OfferDocument) -> Optional[str]:
    """Resolve document URL (public CDN or None for presigned) - DEPRECATED: use generate_presigned_url_for_document"""
    if doc.url:
        return doc.url
    if settings.S3_PUBLIC_BASE_URL:
        return f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{doc.key}"
    return None


def build_media_block(offer: Offer, db: Session) -> OfferMediaBlockResponse:
    """
    Build structured media block with presigned URLs.
    
    Structure:
    - cover: The media identified by offer.cover_media_id (if exists and PUBLIC)
    - promo_video: The media identified by offer.promo_video_media_id (if exists and PUBLIC)
    - gallery: All other PUBLIC media items (excluding cover and promo_video)
    - documents: All PUBLIC documents
    
    Uses bulk queries to avoid SQLAlchemy relationship ambiguity.
    Always returns a valid OfferMediaBlockResponse (even if empty) to avoid 412 errors.
    """
    # Collect cover and promo_video IDs for bulk query
    media_ids_to_fetch = []
    cover_id = offer.cover_media_id
    promo_id = offer.promo_video_media_id
    
    if cover_id:
        media_ids_to_fetch.append(cover_id)
    if promo_id:
        media_ids_to_fetch.append(promo_id)
    
    # Bulk fetch cover and promo_video (if IDs exist)
    cover_promo_media_dict = {}
    if media_ids_to_fetch:
        cover_promo_media = db.query(OfferMedia).filter(
            OfferMedia.id.in_(media_ids_to_fetch),
            OfferMedia.offer_id == offer.id,  # Security: ensure media belongs to this offer
            OfferMedia.visibility == MediaVisibility.PUBLIC
        ).all()
        cover_promo_media_dict = {media.id: media for media in cover_promo_media}
    
    cover_media = cover_promo_media_dict.get(cover_id) if cover_id else None
    promo_video_media = cover_promo_media_dict.get(promo_id) if promo_id else None
    
    # Get all other PUBLIC media (excluding cover and promo_video)
    gallery_media_query = db.query(OfferMedia).filter(
        OfferMedia.offer_id == offer.id,
        OfferMedia.visibility == MediaVisibility.PUBLIC
    )
    
    # Exclude cover and promo_video from gallery
    if cover_id and promo_id:
        gallery_media_query = gallery_media_query.filter(
            ~OfferMedia.id.in_([cover_id, promo_id])
        )
    elif cover_id:
        gallery_media_query = gallery_media_query.filter(OfferMedia.id != cover_id)
    elif promo_id:
        gallery_media_query = gallery_media_query.filter(OfferMedia.id != promo_id)
    
    gallery_media = gallery_media_query.order_by(OfferMedia.sort_order, OfferMedia.created_at).all()
    
    # Build cover response
    cover_response = None
    if cover_media:
        cover_url = generate_presigned_url_for_media(cover_media)
        if cover_url:  # Only include if URL was successfully generated
            cover_response = PresignedMediaItemResponse(
                id=str(cover_media.id),
                type=cover_media.type.value,
                kind="COVER",
                url=cover_url,
                mime_type=cover_media.mime_type,
                size_bytes=cover_media.size_bytes,
                width=cover_media.width,
                height=cover_media.height,
                duration_seconds=cover_media.duration_seconds,
            )
    
    # Build promo_video response
    promo_video_response = None
    if promo_video_media:
        promo_url = generate_presigned_url_for_media(promo_video_media)
        if promo_url:  # Only include if URL was successfully generated
            promo_video_response = PresignedMediaItemResponse(
                id=str(promo_video_media.id),
                type=promo_video_media.type.value,
                kind="PROMO_VIDEO",
                url=promo_url,
                mime_type=promo_video_media.mime_type,
                size_bytes=promo_video_media.size_bytes,
                width=promo_video_media.width,
                height=promo_video_media.height,
                duration_seconds=promo_video_media.duration_seconds,
            )
    
    # Build gallery responses (excluding cover and promo_video)
    gallery_responses = []
    for media in gallery_media:
        gallery_url = generate_presigned_url_for_media(media)
        if gallery_url:  # Only include if URL was successfully generated
            gallery_responses.append(PresignedMediaItemResponse(
                id=str(media.id),
                type=media.type.value,
                kind=None,  # Gallery items don't have a kind
                url=gallery_url,
                mime_type=media.mime_type,
                size_bytes=media.size_bytes,
                width=media.width,
                height=media.height,
                duration_seconds=media.duration_seconds,
            ))
    
    # Get PUBLIC documents
    docs = db.query(OfferDocument).filter(
        OfferDocument.offer_id == offer.id,
        OfferDocument.visibility == DocumentVisibility.PUBLIC
    ).order_by(OfferDocument.created_at.desc()).all()
    
    # Build document responses
    document_responses = []
    for doc in docs:
        doc_url = generate_presigned_url_for_document(doc)
        if doc_url:  # Only include if URL was successfully generated
            document_responses.append(PresignedDocumentItemResponse(
                id=str(doc.id),
                name=doc.name,
                kind=doc.kind.value,
                url=doc_url,
                mime_type=doc.mime_type,
                size_bytes=doc.size_bytes,
            ))
    
    return OfferMediaBlockResponse(
        cover=cover_response,
        promo_video=promo_video_response,
        gallery=gallery_responses,
        documents=document_responses,
    )


def build_offer_response(offer: Offer, db: Session) -> OfferResponse:
    """Build OfferResponse with structured media block containing presigned URLs.
    
    Uses explicit queries to avoid SQLAlchemy relationship ambiguity.
    All media URLs are presigned URLs generated at runtime (never public endpoints).
    """
    # Build structured media block with presigned URLs
    media_block = build_media_block(offer, db)
    
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
        media=media_block,  # Structured media block with presigned URLs
        # Marketing V1.1 fields
        cover_media_id=str(offer.cover_media_id) if offer.cover_media_id else None,
        promo_video_media_id=str(offer.promo_video_media_id) if offer.promo_video_media_id else None,
        cover_url=media_block.cover.url if media_block.cover else None,  # Keep cover_url for backward compatibility
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


def generate_presigned_url_for_article_media(media: ArticleMedia) -> Optional[str]:
    """
    Generate presigned URL for article media.
    Returns None if storage is not configured or if media.url exists (public CDN).
    """
    # If media has a public URL, prefer it
    if media.url:
        return media.url
    
    # Try to generate presigned URL
    try:
        s3_service = get_s3_service()
        return s3_service.generate_presigned_get_url(key=media.key)
    except StorageNotConfiguredError:
        # Storage not configured - return None
        logger.warning(f"Storage not configured, cannot generate presigned URL for article media {media.id}")
        return None
    except Exception as e:
        logger.error(f"Failed to generate presigned URL for article media {media.id}: {str(e)}")
        return None


@router.get(
    "/offers/{offer_id}/articles",
    response_model=List[ArticlePublicListItem],
    summary="Get articles linked to an offer",
    description="List published articles linked to a specific offer. Public endpoint (no authentication required).",
)
async def get_offer_articles(
    offer_id: UUID,
    limit: int = Query(default=10, ge=1, le=50, description="Maximum number of results"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
) -> List[ArticlePublicListItem]:
    """
    Get published articles linked to an offer.
    
    This is a PUBLIC endpoint (no authentication required).
    Returns only articles with status='published'.
    """
    # Verify offer exists
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Get articles linked to this offer (only published)
    articles = db.query(Article).join(Article.offers).filter(
        Offer.id == offer_id,
        Article.status == ArticleStatus.PUBLISHED.value
    ).order_by(Article.published_at.desc().nullslast(), Article.updated_at.desc().nullslast()).limit(limit).offset(offset).all()
    
    results = []
    for article in articles:
        # Get cover URL
        cover_url = None
        if article.cover_media_id:
            cover_media = db.query(ArticleMedia).filter(ArticleMedia.id == article.cover_media_id).first()
            if cover_media:
                cover_url = generate_presigned_url_for_article_media(cover_media)
        
        results.append(ArticlePublicListItem(
            id=str(article.id),
            slug=article.slug,
            title=article.title,
            subtitle=article.subtitle,
            excerpt=article.excerpt,
            cover_url=cover_url,
            author_name=article.author_name,
            published_at=article.published_at.isoformat() if article.published_at else None,
            tags=article.tags if article.tags else [],
            is_featured=article.is_featured,
        ))
    
    return results


def build_timeline_event_response_public(event: OfferTimelineEvent, db: Session) -> TimelineEventResponse:
    """Build timeline event response for public API with article info if linked and published"""
    article_info = None
    if event.article_id:
        article = db.query(Article).filter(Article.id == event.article_id).first()
        # Only include article if it's published
        if article and article.status == ArticleStatus.PUBLISHED.value:
            # Get cover URL if available
            cover_url = None
            if article.cover_media_id:
                cover_media = db.query(ArticleMedia).filter(ArticleMedia.id == article.cover_media_id).first()
                if cover_media:
                    cover_url = generate_presigned_url_for_article_media(cover_media)
            
            article_info = TimelineEventArticleInfo(
                id=str(article.id),
                title=article.title,
                slug=article.slug,
                published_at=article.published_at.isoformat() if article.published_at else None,
                cover_url=cover_url,
            )
    
    return TimelineEventResponse(
        id=str(event.id),
        title=event.title,
        description=event.description,
        occurred_at=event.occurred_at.isoformat() if event.occurred_at else None,
        sort_order=event.sort_order,
        article=article_info,
        created_at=event.created_at.isoformat(),
        updated_at=event.updated_at.isoformat() if event.updated_at else None,
    )


@router.get(
    "/offers/{offer_id}/timeline",
    response_model=List[TimelineEventResponse],
    summary="Get timeline events for an offer",
    description="List all timeline events (project progress) for an offer, sorted by order and date. Public endpoint (no authentication required).",
)
async def get_offer_timeline(
    offer_id: UUID,
    db: Session = Depends(get_db),
) -> List[TimelineEventResponse]:
    """
    Get timeline events for an offer.
    
    This is a PUBLIC endpoint (no authentication required).
    Returns timeline events sorted by sort_order ASC, then occurred_at ASC.
    Linked articles are only included if they are published.
    """
    # Verify offer exists
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Get timeline events sorted by sort_order ASC, then occurred_at ASC
    events = db.query(OfferTimelineEvent).filter(
        OfferTimelineEvent.offer_id == offer_id
    ).order_by(
        OfferTimelineEvent.sort_order.asc(),
        OfferTimelineEvent.occurred_at.asc().nullslast()
    ).all()
    
    return [build_timeline_event_response_public(event, db) for event in events]
