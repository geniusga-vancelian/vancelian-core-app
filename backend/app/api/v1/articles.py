"""
Public API - Articles (Blog/News)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, List
from datetime import datetime, timezone
import logging

from app.infrastructure.database import get_db
from app.core.articles.models import Article, ArticleMedia, ArticleStatus, ArticleMediaType
from app.core.offers.models import Offer
from app.schemas.articles import (
    ArticlePublicListItem,
    ArticlePublicDetail,
    ArticleMediaBlockResponse,
    PresignedArticleMediaItemResponse,
    OfferMinimalResponse,
)
from app.auth.dependencies import require_user_role
from app.auth.oidc import Principal
from app.services.storage.s3_service import get_s3_service
from app.services.storage.exceptions import StorageNotConfiguredError

logger = logging.getLogger(__name__)

router = APIRouter()


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


def build_article_media_block(article: Article, db: Session) -> ArticleMediaBlockResponse:
    """
    Build structured media block with presigned URLs for article.
    
    Structure:
    - cover: The media identified by article.cover_media_id (if exists)
    - promo_video: The media identified by article.promo_video_media_id (if exists)
    - gallery: All other image/video items (excluding cover and promo_video)
    - documents: All document items
    
    Uses bulk queries to avoid SQLAlchemy relationship ambiguity.
    Always returns a valid ArticleMediaBlockResponse (even if empty).
    """
    # Collect cover and promo_video IDs for bulk query
    media_ids_to_fetch = []
    cover_id = article.cover_media_id
    promo_id = article.promo_video_media_id
    
    if cover_id:
        media_ids_to_fetch.append(cover_id)
    if promo_id:
        media_ids_to_fetch.append(promo_id)
    
    # Bulk fetch cover and promo_video (if IDs exist)
    cover_promo_media_dict = {}
    if media_ids_to_fetch:
        cover_promo_media = db.query(ArticleMedia).filter(
            ArticleMedia.id.in_(media_ids_to_fetch),
            ArticleMedia.article_id == article.id,  # Security: ensure media belongs to this article
        ).all()
        cover_promo_media_dict = {media.id: media for media in cover_promo_media}
    
    cover_media = cover_promo_media_dict.get(cover_id) if cover_id else None
    promo_video_media = cover_promo_media_dict.get(promo_id) if promo_id else None
    
    # Get all other media (excluding cover and promo_video) for gallery
    gallery_media_query = db.query(ArticleMedia).filter(
        ArticleMedia.article_id == article.id,
        ArticleMedia.type.in_([ArticleMediaType.IMAGE, ArticleMediaType.VIDEO])
    )
    
    # Exclude cover and promo_video from gallery
    if cover_id and promo_id:
        gallery_media_query = gallery_media_query.filter(
            ~ArticleMedia.id.in_([cover_id, promo_id])
        )
    elif cover_id:
        gallery_media_query = gallery_media_query.filter(ArticleMedia.id != cover_id)
    elif promo_id:
        gallery_media_query = gallery_media_query.filter(ArticleMedia.id != promo_id)
    
    gallery_media = gallery_media_query.order_by(ArticleMedia.created_at).all()
    
    # Get all documents
    document_media = db.query(ArticleMedia).filter(
        ArticleMedia.article_id == article.id,
        ArticleMedia.type == ArticleMediaType.DOCUMENT
    ).order_by(ArticleMedia.created_at).all()
    
    # Build cover response
    cover_response = None
    if cover_media:
        cover_url = generate_presigned_url_for_article_media(cover_media)
        if cover_url:  # Only include if URL was successfully generated
            cover_response = PresignedArticleMediaItemResponse(
                id=str(cover_media.id),
                type=cover_media.type.value,
                kind="cover",
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
        promo_url = generate_presigned_url_for_article_media(promo_video_media)
        if promo_url:  # Only include if URL was successfully generated
            promo_video_response = PresignedArticleMediaItemResponse(
                id=str(promo_video_media.id),
                type=promo_video_media.type.value,
                kind="promo_video",
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
        gallery_url = generate_presigned_url_for_article_media(media)
        if gallery_url:  # Only include if URL was successfully generated
            gallery_responses.append(PresignedArticleMediaItemResponse(
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
    
    # Build document responses
    document_responses = []
    for media in document_media:
        doc_url = generate_presigned_url_for_article_media(media)
        if doc_url:  # Only include if URL was successfully generated
            document_responses.append(PresignedArticleMediaItemResponse(
                id=str(media.id),
                type=media.type.value,
                kind="document",
                url=doc_url,
                mime_type=media.mime_type,
                size_bytes=media.size_bytes,
                width=media.width,
                height=media.height,
                duration_seconds=media.duration_seconds,
            ))
    
    return ArticleMediaBlockResponse(
        cover=cover_response,
        promo_video=promo_video_response,
        gallery=gallery_responses,
        documents=document_responses,
    )


@router.get(
    "/articles",
    response_model=List[ArticlePublicListItem],
    summary="List published articles",
    description="List published articles with optional filters. Requires USER role.",
)
async def list_articles(
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    featured: Optional[bool] = Query(None, description="Filter by featured flag"),
    offer_id: Optional[UUID] = Query(None, description="Filter articles linked to this offer"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> List[ArticlePublicListItem]:
    """List published articles"""
    query = db.query(Article).filter(Article.status == ArticleStatus.PUBLISHED.value)
    
    # Filter by tag (if provided)
    if tag:
        query = query.filter(Article.tags.contains([tag]))
    
    # Filter by featured (if provided)
    if featured is not None:
        query = query.filter(Article.is_featured == featured)
    
    # Filter by offer (via many-to-many relationship)
    if offer_id:
        query = query.join(Article.offers).filter(Offer.id == offer_id)
    
    # Order by published_at desc (most recent first)
    articles = query.order_by(Article.published_at.desc().nullslast()).limit(limit).offset(offset).all()
    
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


@router.get(
    "/articles/{slug}",
    response_model=ArticlePublicDetail,
    summary="Get article by slug",
    description="Get detailed information about a published article by slug. Requires USER role.",
)
async def get_article_by_slug(
    slug: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> ArticlePublicDetail:
    """Get published article by slug"""
    article = db.query(Article).filter(
        Article.slug == slug,
        Article.status == ArticleStatus.PUBLISHED.value
    ).first()
    
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ARTICLE_NOT_FOUND"
        )
    
    # Build media block
    media_block = build_article_media_block(article, db)
    
    # Get linked offers (minimal info)
    offer_responses = []
    if article.offers:
        for offer in article.offers:
            offer_responses.append(OfferMinimalResponse(
                id=str(offer.id),
                code=offer.code,
                name=offer.name,
            ))
    
    return ArticlePublicDetail(
        id=str(article.id),
        slug=article.slug,
        title=article.title,
        subtitle=article.subtitle,
        excerpt=article.excerpt,
        content_markdown=article.content_markdown,
        content_html=article.content_html,
        author_name=article.author_name,
        published_at=article.published_at.isoformat() if article.published_at else None,
        created_at=article.created_at.isoformat(),
        updated_at=article.updated_at.isoformat() if article.updated_at else None,
        tags=article.tags if article.tags else [],
        is_featured=article.is_featured,
        media=media_block,
        offers=offer_responses,
        seo_title=article.seo_title or article.title,
        seo_description=article.seo_description or article.excerpt,
    )



