"""
Admin API - Offer Timeline Events management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from datetime import datetime

from app.infrastructure.database import get_db
from app.core.offers.models import Offer, OfferTimelineEvent
from app.core.articles.models import Article, ArticleStatus
from app.schemas.offers_timeline import (
    TimelineEventResponse,
    TimelineEventCreateIn,
    TimelineEventUpdateIn,
    TimelineReorderIn,
    TimelineEventArticleInfo,
)
from app.auth.dependencies import require_admin_role
from app.auth.oidc import Principal

router = APIRouter()


def build_timeline_event_response(event: OfferTimelineEvent, db: Session) -> TimelineEventResponse:
    """Build timeline event response with article info if linked"""
    article_info = None
    if event.article_id:
        article = db.query(Article).filter(Article.id == event.article_id).first()
        if article and article.status == ArticleStatus.PUBLISHED.value:
            # Get cover URL if available
            cover_url = None
            if article.cover_media_id:
                from app.core.articles.models import ArticleMedia
                from app.api.v1.articles import generate_presigned_url_for_article_media
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
    description="List all timeline events for an offer, sorted by order and date. Requires ADMIN role.",
)
async def get_offer_timeline(
    offer_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> List[TimelineEventResponse]:
    """Get timeline events for an offer"""
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
    
    return [build_timeline_event_response(event, db) for event in events]


@router.post(
    "/offers/{offer_id}/timeline",
    response_model=TimelineEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a timeline event",
    description="Create a new timeline event for an offer. Requires ADMIN role.",
)
async def create_timeline_event(
    offer_id: UUID,
    request: TimelineEventCreateIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> TimelineEventResponse:
    """Create a timeline event"""
    # Verify offer exists
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Verify article exists if provided
    article_id = None
    if request.article_id:
        try:
            article_id = UUID(request.article_id)
            article = db.query(Article).filter(Article.id == article_id).first()
            if not article:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="ARTICLE_NOT_FOUND"
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="INVALID_ARTICLE_ID"
            )
    
    # Parse occurred_at if provided
    occurred_at = None
    if request.occurred_at:
        try:
            occurred_at = datetime.fromisoformat(request.occurred_at.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="INVALID_DATE_FORMAT"
            )
    
    # Create event
    event = OfferTimelineEvent(
        offer_id=offer_id,
        title=request.title,
        description=request.description,
        occurred_at=occurred_at,
        article_id=article_id,
        sort_order=request.sort_order or 0,
    )
    
    db.add(event)
    db.commit()
    db.refresh(event)
    
    return build_timeline_event_response(event, db)


@router.patch(
    "/offers/{offer_id}/timeline/{event_id}",
    response_model=TimelineEventResponse,
    summary="Update a timeline event",
    description="Update an existing timeline event. Requires ADMIN role.",
)
async def update_timeline_event(
    offer_id: UUID,
    event_id: UUID,
    request: TimelineEventUpdateIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> TimelineEventResponse:
    """Update a timeline event"""
    # Verify offer exists
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Verify event exists and belongs to offer
    event = db.query(OfferTimelineEvent).filter(
        OfferTimelineEvent.id == event_id,
        OfferTimelineEvent.offer_id == offer_id
    ).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TIMELINE_EVENT_NOT_FOUND"
        )
    
    # Update fields
    if request.title is not None:
        event.title = request.title
    if request.description is not None:
        event.description = request.description
    if request.occurred_at is not None:
        if request.occurred_at:
            try:
                event.occurred_at = datetime.fromisoformat(request.occurred_at.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="INVALID_DATE_FORMAT"
                )
        else:
            event.occurred_at = None
    if request.article_id is not None:
        if request.article_id:
            try:
                article_id = UUID(request.article_id)
                article = db.query(Article).filter(Article.id == article_id).first()
                if not article:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="ARTICLE_NOT_FOUND"
                    )
                event.article_id = article_id
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="INVALID_ARTICLE_ID"
                )
        else:
            event.article_id = None
    if request.sort_order is not None:
        event.sort_order = request.sort_order
    
    db.commit()
    db.refresh(event)
    
    return build_timeline_event_response(event, db)


@router.delete(
    "/offers/{offer_id}/timeline/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a timeline event",
    description="Delete a timeline event. Requires ADMIN role.",
)
async def delete_timeline_event(
    offer_id: UUID,
    event_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
):
    """Delete a timeline event"""
    # Verify offer exists
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Verify event exists and belongs to offer
    event = db.query(OfferTimelineEvent).filter(
        OfferTimelineEvent.id == event_id,
        OfferTimelineEvent.offer_id == offer_id
    ).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TIMELINE_EVENT_NOT_FOUND"
        )
    
    db.delete(event)
    db.commit()


@router.post(
    "/offers/{offer_id}/timeline/reorder",
    response_model=List[TimelineEventResponse],
    summary="Reorder timeline events",
    description="Update sort orders for multiple timeline events. Requires ADMIN role.",
)
async def reorder_timeline_events(
    offer_id: UUID,
    request: TimelineReorderIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> List[TimelineEventResponse]:
    """Reorder timeline events"""
    # Verify offer exists
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Get all event IDs for this offer
    event_ids = {str(e.id) for e in db.query(OfferTimelineEvent.id).filter(
        OfferTimelineEvent.offer_id == offer_id
    ).all()}
    
    # Verify all requested IDs belong to this offer
    requested_ids = {item.id for item in request.items}
    if not requested_ids.issubset(event_ids):
        missing = requested_ids - event_ids
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"TIMELINE_EVENTS_NOT_FOUND: {', '.join(missing)}"
        )
    
    # Update sort orders in a transaction
    try:
        for item in request.items:
            event = db.query(OfferTimelineEvent).filter(
                OfferTimelineEvent.id == UUID(item.id),
                OfferTimelineEvent.offer_id == offer_id
            ).first()
            if event:
                event.sort_order = item.sort_order
        
        db.commit()
        
        # Return updated events
        events = db.query(OfferTimelineEvent).filter(
            OfferTimelineEvent.offer_id == offer_id
        ).order_by(
            OfferTimelineEvent.sort_order.asc(),
            OfferTimelineEvent.occurred_at.asc().nullslast()
        ).all()
        
        return [build_timeline_event_response(event, db) for event in events]
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"REORDER_FAILED: {str(e)}"
        )

