"""
Admin API - Articles management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from uuid import UUID
from typing import Optional, List
from datetime import datetime, timezone

from app.infrastructure.database import get_db
from app.core.articles.models import Article, ArticleStatus
from app.core.offers.models import Offer
from app.schemas.articles import (
    ArticleAdminCreateIn,
    ArticleAdminUpdateIn,
    ArticleAdminListItem,
    ArticleAdminDetail,
    ArticleLinkOffersRequest,
    ArticleLinkOfferRequest,
)
from app.auth.dependencies import require_admin_role
from app.auth.oidc import Principal

router = APIRouter()


@router.post(
    "/articles",
    response_model=ArticleAdminDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new article",
    description="Create a new article in DRAFT status. Requires ADMIN role.",
)
async def create_article(
    request: ArticleAdminCreateIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> ArticleAdminDetail:
    """Create a new article"""
    # Check if slug already exists
    existing = db.query(Article).filter(Article.slug == request.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ARTICLE_SLUG_EXISTS"
        )
    
    # Create article
    article = Article(
        slug=request.slug,
        title=request.title,
        subtitle=request.subtitle,
        excerpt=request.excerpt,
        content_markdown=request.content_markdown,
        author_name=request.author_name,
        seo_title=request.seo_title or request.title,
        seo_description=request.seo_description,
        tags=request.tags or [],
        is_featured=request.is_featured,
        status=ArticleStatus.DRAFT.value,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    
    # Get media list (empty for new article)
    media_list = []
    
    return ArticleAdminDetail(
        id=str(article.id),
        slug=article.slug,
        status=article.status,
        title=article.title,
        subtitle=article.subtitle,
        excerpt=article.excerpt,
        content_markdown=article.content_markdown,
        content_html=article.content_html,
        cover_media_id=str(article.cover_media_id) if article.cover_media_id else None,
        promo_video_media_id=str(article.promo_video_media_id) if article.promo_video_media_id else None,
        author_name=article.author_name,
        published_at=article.published_at.isoformat() if article.published_at else None,
        created_at=article.created_at.isoformat(),
        updated_at=article.updated_at.isoformat() if article.updated_at else None,
        seo_title=article.seo_title,
        seo_description=article.seo_description,
        tags=article.tags if article.tags else [],
        is_featured=article.is_featured,
        allow_comments=article.allow_comments,
        media=media_list,
        offer_ids=[],
    )


@router.get(
    "/articles",
    response_model=List[ArticleAdminListItem],
    summary="List articles",
    description="List all articles with optional filters. Requires ADMIN role.",
)
async def list_articles(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (draft, published, archived)"),
    featured: Optional[bool] = Query(None, description="Filter by featured flag"),
    offer_id: Optional[UUID] = Query(None, description="Filter articles linked to this offer"),
    search: Optional[str] = Query(None, description="Search in title/subtitle/excerpt"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> List[ArticleAdminListItem]:
    """List articles with filters"""
    query = db.query(Article)
    
    if status_filter:
        if status_filter not in ["draft", "published", "archived"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="INVALID_STATUS"
            )
        query = query.filter(Article.status == status_filter)
    
    if featured is not None:
        query = query.filter(Article.is_featured == featured)
    
    if offer_id:
        query = query.join(Article.offers).filter(Offer.id == offer_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Article.title.ilike(search_term),
                Article.subtitle.ilike(search_term),
                Article.excerpt.ilike(search_term),
            )
        )
    
    articles = query.order_by(Article.created_at.desc()).limit(limit).offset(offset).all()
    
    return [
        ArticleAdminListItem(
            id=str(article.id),
            slug=article.slug,
            title=article.title,
            status=article.status,
            published_at=article.published_at.isoformat() if article.published_at else None,
            created_at=article.created_at.isoformat(),
            updated_at=article.updated_at.isoformat() if article.updated_at else None,
            is_featured=article.is_featured,
        )
        for article in articles
    ]


@router.get(
    "/articles/{article_id}",
    response_model=ArticleAdminDetail,
    summary="Get article details",
    description="Get detailed information about a specific article. Requires ADMIN role.",
)
async def get_article(
    article_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> ArticleAdminDetail:
    """Get article by ID"""
    article = db.query(Article).filter(Article.id == article_id).first()
    
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ARTICLE_NOT_FOUND"
        )
    
    # Get media list
    from app.core.articles.models import ArticleMedia
    from app.schemas.articles import ArticleMediaOut
    media_list = db.query(ArticleMedia).filter(
        ArticleMedia.article_id == article_id
    ).order_by(ArticleMedia.created_at).all()
    
    media_out = [
        ArticleMediaOut(
            id=str(m.id),
            type=m.type.value,
            key=m.key,
            url=m.url,
            mime_type=m.mime_type,
            size_bytes=m.size_bytes,
            width=m.width,
            height=m.height,
            duration_seconds=m.duration_seconds,
            created_at=m.created_at.isoformat(),
        )
        for m in media_list
    ]
    
    # Get linked offer IDs
    offer_ids = [str(offer.id) for offer in article.offers] if article.offers else []
    
    return ArticleAdminDetail(
        id=str(article.id),
        slug=article.slug,
        status=article.status,
        title=article.title,
        subtitle=article.subtitle,
        excerpt=article.excerpt,
        content_markdown=article.content_markdown,
        content_html=article.content_html,
        cover_media_id=str(article.cover_media_id) if article.cover_media_id else None,
        promo_video_media_id=str(article.promo_video_media_id) if article.promo_video_media_id else None,
        author_name=article.author_name,
        published_at=article.published_at.isoformat() if article.published_at else None,
        created_at=article.created_at.isoformat(),
        updated_at=article.updated_at.isoformat() if article.updated_at else None,
        seo_title=article.seo_title,
        seo_description=article.seo_description,
        tags=article.tags if article.tags else [],
        is_featured=article.is_featured,
        allow_comments=article.allow_comments,
        media=media_out,
        offer_ids=offer_ids,
    )


@router.patch(
    "/articles/{article_id}",
    response_model=ArticleAdminDetail,
    summary="Update article",
    description="Update article fields. Requires ADMIN role.",
)
async def update_article(
    article_id: UUID,
    request: ArticleAdminUpdateIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> ArticleAdminDetail:
    """Update article"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ARTICLE_NOT_FOUND"
        )
    
    # Check slug uniqueness if changed
    if request.slug is not None and request.slug != article.slug:
        existing = db.query(Article).filter(Article.slug == request.slug).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="ARTICLE_SLUG_EXISTS"
            )
        article.slug = request.slug
    
    # Update fields
    if request.title is not None:
        article.title = request.title
    if request.subtitle is not None:
        article.subtitle = request.subtitle
    if request.excerpt is not None:
        article.excerpt = request.excerpt
    if request.content_markdown is not None:
        article.content_markdown = request.content_markdown
    if request.content_html is not None:
        article.content_html = request.content_html
    if request.author_name is not None:
        article.author_name = request.author_name
    if request.seo_title is not None:
        article.seo_title = request.seo_title
    if request.seo_description is not None:
        article.seo_description = request.seo_description
    if request.tags is not None:
        article.tags = request.tags
    if request.is_featured is not None:
        article.is_featured = request.is_featured
    if request.status is not None:
        article.status = request.status
    
    db.commit()
    db.refresh(article)
    
    # Get media list
    from app.core.articles.models import ArticleMedia
    from app.schemas.articles import ArticleMediaOut
    media_list = db.query(ArticleMedia).filter(
        ArticleMedia.article_id == article_id
    ).order_by(ArticleMedia.created_at).all()
    
    media_out = [
        ArticleMediaOut(
            id=str(m.id),
            type=m.type.value,
            key=m.key,
            url=m.url,
            mime_type=m.mime_type,
            size_bytes=m.size_bytes,
            width=m.width,
            height=m.height,
            duration_seconds=m.duration_seconds,
            created_at=m.created_at.isoformat(),
        )
        for m in media_list
    ]
    
    # Get linked offer IDs
    offer_ids = [str(offer.id) for offer in article.offers] if article.offers else []
    
    return ArticleAdminDetail(
        id=str(article.id),
        slug=article.slug,
        status=article.status,
        title=article.title,
        subtitle=article.subtitle,
        excerpt=article.excerpt,
        content_markdown=article.content_markdown,
        content_html=article.content_html,
        cover_media_id=str(article.cover_media_id) if article.cover_media_id else None,
        promo_video_media_id=str(article.promo_video_media_id) if article.promo_video_media_id else None,
        author_name=article.author_name,
        published_at=article.published_at.isoformat() if article.published_at else None,
        created_at=article.created_at.isoformat(),
        updated_at=article.updated_at.isoformat() if article.updated_at else None,
        seo_title=article.seo_title,
        seo_description=article.seo_description,
        tags=article.tags if article.tags else [],
        is_featured=article.is_featured,
        allow_comments=article.allow_comments,
        media=media_out,
        offer_ids=offer_ids,
    )


@router.post(
    "/articles/{article_id}/publish",
    response_model=ArticleAdminDetail,
    summary="Publish article",
    description="Set article status to published and set published_at timestamp. Requires ADMIN role.",
)
async def publish_article(
    article_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> ArticleAdminDetail:
    """Publish article"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ARTICLE_NOT_FOUND"
        )
    
    article.status = ArticleStatus.PUBLISHED.value
    if not article.published_at:
        article.published_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(article)
    
    # Get media list
    from app.core.articles.models import ArticleMedia
    from app.schemas.articles import ArticleMediaOut
    media_list = db.query(ArticleMedia).filter(
        ArticleMedia.article_id == article_id
    ).order_by(ArticleMedia.created_at).all()
    
    media_out = [
        ArticleMediaOut(
            id=str(m.id),
            type=m.type.value,
            key=m.key,
            url=m.url,
            mime_type=m.mime_type,
            size_bytes=m.size_bytes,
            width=m.width,
            height=m.height,
            duration_seconds=m.duration_seconds,
            created_at=m.created_at.isoformat(),
        )
        for m in media_list
    ]
    
    # Get linked offer IDs
    offer_ids = [str(offer.id) for offer in article.offers] if article.offers else []
    
    return ArticleAdminDetail(
        id=str(article.id),
        slug=article.slug,
        status=article.status,
        title=article.title,
        subtitle=article.subtitle,
        excerpt=article.excerpt,
        content_markdown=article.content_markdown,
        content_html=article.content_html,
        cover_media_id=str(article.cover_media_id) if article.cover_media_id else None,
        promo_video_media_id=str(article.promo_video_media_id) if article.promo_video_media_id else None,
        author_name=article.author_name,
        published_at=article.published_at.isoformat() if article.published_at else None,
        created_at=article.created_at.isoformat(),
        updated_at=article.updated_at.isoformat() if article.updated_at else None,
        seo_title=article.seo_title,
        seo_description=article.seo_description,
        tags=article.tags if article.tags else [],
        is_featured=article.is_featured,
        allow_comments=article.allow_comments,
        media=media_out,
        offer_ids=offer_ids,
    )


@router.post(
    "/articles/{article_id}/archive",
    response_model=ArticleAdminDetail,
    summary="Archive article",
    description="Set article status to archived. Requires ADMIN role.",
)
async def archive_article(
    article_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> ArticleAdminDetail:
    """Archive article"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ARTICLE_NOT_FOUND"
        )
    
    article.status = ArticleStatus.ARCHIVED.value
    
    db.commit()
    db.refresh(article)
    
    # Get media list
    from app.core.articles.models import ArticleMedia
    from app.schemas.articles import ArticleMediaOut
    media_list = db.query(ArticleMedia).filter(
        ArticleMedia.article_id == article_id
    ).order_by(ArticleMedia.created_at).all()
    
    media_out = [
        ArticleMediaOut(
            id=str(m.id),
            type=m.type.value,
            key=m.key,
            url=m.url,
            mime_type=m.mime_type,
            size_bytes=m.size_bytes,
            width=m.width,
            height=m.height,
            duration_seconds=m.duration_seconds,
            created_at=m.created_at.isoformat(),
        )
        for m in media_list
    ]
    
    # Get linked offer IDs
    offer_ids = [str(offer.id) for offer in article.offers] if article.offers else []
    
    return ArticleAdminDetail(
        id=str(article.id),
        slug=article.slug,
        status=article.status,
        title=article.title,
        subtitle=article.subtitle,
        excerpt=article.excerpt,
        content_markdown=article.content_markdown,
        content_html=article.content_html,
        cover_media_id=str(article.cover_media_id) if article.cover_media_id else None,
        promo_video_media_id=str(article.promo_video_media_id) if article.promo_video_media_id else None,
        author_name=article.author_name,
        published_at=article.published_at.isoformat() if article.published_at else None,
        created_at=article.created_at.isoformat(),
        updated_at=article.updated_at.isoformat() if article.updated_at else None,
        seo_title=article.seo_title,
        seo_description=article.seo_description,
        tags=article.tags if article.tags else [],
        is_featured=article.is_featured,
        allow_comments=article.allow_comments,
        media=media_out,
        offer_ids=offer_ids,
    )


@router.put(
    "/articles/{article_id}/offers",
    response_model=ArticleAdminDetail,
    summary="Link/unlink offers to article",
    description="Replace all offer links for this article. Requires ADMIN role.",
)
async def link_article_offers(
    article_id: UUID,
    request: ArticleLinkOffersRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> ArticleAdminDetail:
    """Link/unlink offers to article"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ARTICLE_NOT_FOUND"
        )
    
    # Validate all offer IDs exist
    offer_ids = [UUID(offer_id_str) for offer_id_str in request.offer_ids]
    offers = db.query(Offer).filter(Offer.id.in_(offer_ids)).all()
    if len(offers) != len(offer_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SOME_OFFERS_NOT_FOUND"
        )
    
    # Replace offers relationship
    article.offers = offers
    db.commit()
    db.refresh(article)
    
    # Get media list
    from app.core.articles.models import ArticleMedia
    from app.schemas.articles import ArticleMediaOut
    media_list = db.query(ArticleMedia).filter(
        ArticleMedia.article_id == article_id
    ).order_by(ArticleMedia.created_at).all()
    
    media_out = [
        ArticleMediaOut(
            id=str(m.id),
            type=m.type.value,
            key=m.key,
            url=m.url,
            mime_type=m.mime_type,
            size_bytes=m.size_bytes,
            width=m.width,
            height=m.height,
            duration_seconds=m.duration_seconds,
            created_at=m.created_at.isoformat(),
        )
        for m in media_list
    ]
    
    # Get linked offer IDs
    offer_ids_result = [str(offer.id) for offer in article.offers] if article.offers else []
    
    return ArticleAdminDetail(
        id=str(article.id),
        slug=article.slug,
        status=article.status,
        title=article.title,
        subtitle=article.subtitle,
        excerpt=article.excerpt,
        content_markdown=article.content_markdown,
        content_html=article.content_html,
        cover_media_id=str(article.cover_media_id) if article.cover_media_id else None,
        promo_video_media_id=str(article.promo_video_media_id) if article.promo_video_media_id else None,
        author_name=article.author_name,
        published_at=article.published_at.isoformat() if article.published_at else None,
        created_at=article.created_at.isoformat(),
        updated_at=article.updated_at.isoformat() if article.updated_at else None,
        seo_title=article.seo_title,
        seo_description=article.seo_description,
        tags=article.tags if article.tags else [],
        is_featured=article.is_featured,
        allow_comments=article.allow_comments,
        media=media_out,
        offer_ids=offer_ids_result,
    )


@router.put(
    "/articles/{article_id}/offer",
    response_model=ArticleAdminDetail,
    summary="Link/unlink a single offer to article",
    description="Link a single offer to this article, or unlink if offer_id is null. Replaces any existing links. Requires ADMIN role.",
)
async def link_article_offer(
    article_id: UUID,
    request: ArticleLinkOfferRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> ArticleAdminDetail:
    """Link/unlink a single offer to article"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ARTICLE_NOT_FOUND"
        )
    
    # Convert offer_ids list (empty or single item)
    offer_ids_list = [request.offer_id] if request.offer_id else []
    
    # Validate offer ID exists if provided
    if request.offer_id:
        try:
            offer_uuid = UUID(request.offer_id)
            offer = db.query(Offer).filter(Offer.id == offer_uuid).first()
            if not offer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="OFFER_NOT_FOUND"
                )
            # Replace offers relationship (single offer or empty list)
            article.offers = [offer]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="INVALID_OFFER_ID"
            )
    else:
        # Unlink: clear all offers
        article.offers = []
    
    db.commit()
    db.refresh(article)
    
    # Get media list
    from app.core.articles.models import ArticleMedia
    from app.schemas.articles import ArticleMediaOut
    media_list = db.query(ArticleMedia).filter(
        ArticleMedia.article_id == article_id
    ).order_by(ArticleMedia.created_at).all()
    
    media_out = [
        ArticleMediaOut(
            id=str(m.id),
            type=m.type.value,
            key=m.key,
            url=m.url,
            mime_type=m.mime_type,
            size_bytes=m.size_bytes,
            width=m.width,
            height=m.height,
            duration_seconds=m.duration_seconds,
            created_at=m.created_at.isoformat(),
        )
        for m in media_list
    ]
    
    # Get linked offer IDs
    offer_ids_result = [str(offer.id) for offer in article.offers] if article.offers else []
    
    return ArticleAdminDetail(
        id=str(article.id),
        slug=article.slug,
        status=article.status,
        title=article.title,
        subtitle=article.subtitle,
        excerpt=article.excerpt,
        content_markdown=article.content_markdown,
        content_html=article.content_html,
        cover_media_id=str(article.cover_media_id) if article.cover_media_id else None,
        promo_video_media_id=str(article.promo_video_media_id) if article.promo_video_media_id else None,
        author_name=article.author_name,
        published_at=article.published_at.isoformat() if article.published_at else None,
        created_at=article.created_at.isoformat(),
        updated_at=article.updated_at.isoformat() if article.updated_at else None,
        seo_title=article.seo_title,
        seo_description=article.seo_description,
        tags=article.tags if article.tags else [],
        is_featured=article.is_featured,
        allow_comments=article.allow_comments,
        media=media_out,
        offer_ids=offer_ids_result,
    )
