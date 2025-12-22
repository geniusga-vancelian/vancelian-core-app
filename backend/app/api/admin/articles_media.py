"""
Admin API - Articles Media management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional

from app.infrastructure.database import get_db
from app.core.articles.models import Article, ArticleMedia, ArticleMediaType
from app.schemas.articles import (
    ArticlePresignUploadRequest,
    ArticlePresignUploadResponse,
    ArticleCreateMediaRequest,
    ArticleMediaOut,
)
from app.auth.dependencies import require_admin_role
from app.auth.oidc import Principal
from app.services.storage.s3_service import get_s3_service
from app.services.storage.exceptions import StorageNotConfiguredError
from app.infrastructure.settings import get_settings
from app.utils.trace_id import get_trace_id
from fastapi import Request

router = APIRouter()
settings = get_settings()


def get_article_media_type_value(media_type) -> str:
    """Get the string value from media type (handles both enum and string)"""
    if isinstance(media_type, str):
        return media_type
    return media_type.value if hasattr(media_type, 'value') else str(media_type)


def resolve_article_media_url(media: ArticleMedia, generate_presigned: bool = False) -> Optional[str]:
    """Resolve article media URL (public CDN, presigned, or None)"""
    if media.url:
        return media.url
    if settings.S3_PUBLIC_BASE_URL:
        return f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{media.key}"
    if generate_presigned:
        try:
            s3_service = get_s3_service()
            return s3_service.generate_presigned_get_url(key=media.key)
        except (StorageNotConfiguredError, Exception):
            return None
    return None


@router.post(
    "/articles/{article_id}/uploads/presign",
    response_model=ArticlePresignUploadResponse,
    summary="Generate presigned upload URL for article media",
    description="Generate a presigned PUT URL for uploading article media. Requires ADMIN role.",
)
async def presign_article_upload(
    article_id: UUID,
    request: ArticlePresignUploadRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> ArticlePresignUploadResponse:
    """Generate presigned upload URL for article media"""
    # Verify article exists
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ARTICLE_NOT_FOUND"
        )
    
    # Validate upload type
    if request.upload_type not in ["image", "video", "document"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="INVALID_UPLOAD_TYPE"
        )
    
    # Get S3 service
    s3_service = get_s3_service()
    
    # Basic size validation (aligned with offers_media)
    max_size = settings.S3_MAX_IMAGE_SIZE if request.upload_type == "image" else (
        settings.S3_MAX_VIDEO_SIZE if request.upload_type == "video" else settings.S3_MAX_DOCUMENT_SIZE
    )
    if request.size_bytes > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size {request.size_bytes} bytes exceeds maximum allowed size {max_size} bytes"
        )
    
    # Build object key
    key = s3_service.build_article_object_key(article_id, request.file_name, request.upload_type)
    
    # Generate presigned PUT URL (same pattern as offers_media)
    try:
        upload_url = s3_service.generate_presigned_put_url(
            key=key,
            mime_type=request.mime_type,
        )
    except StorageNotConfiguredError as e:
        # Storage not configured - return 412 Precondition Failed (same as offers_media)
        trace_id = get_trace_id(http_request)
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail={
                "code": e.code,
                "message": e.message,
                "trace_id": trace_id,
            }
        )
    except ValueError as e:
        # Other boto3 errors
        trace_id = get_trace_id(http_request)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "STORAGE_ERROR",
                "message": str(e),
                "trace_id": trace_id,
            }
        )
    
    return ArticlePresignUploadResponse(
        upload_url=upload_url,
        key=key,
        required_headers={"Content-Type": request.mime_type},
        expires_in=settings.S3_PRESIGN_EXPIRES_SECONDS,
    )


@router.post(
    "/articles/{article_id}/media",
    response_model=ArticleMediaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create article media metadata",
    description="Create article media metadata after successful upload. Requires ADMIN role.",
)
async def create_article_media(
    article_id: UUID,
    request: ArticleCreateMediaRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> ArticleMediaOut:
    """Create article media metadata after upload"""
    # Verify article exists
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ARTICLE_NOT_FOUND"
        )
    
    # Validate media type and get enum value
    # PostgreSQL enum expects lowercase: "image", "video", "document"
    try:
        # Convert input to enum member (e.g., "image" -> ArticleMediaType.IMAGE)
        media_type_enum = ArticleMediaType[request.type.upper()]
        # Get the enum value (lowercase string: "image", "video", "document")
        media_type_value = media_type_enum.value
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid media type: {request.type}. Expected image, video, or document"
        )
    
    # Create media record
    # Use the enum value string directly to match PostgreSQL enum values
    # SQLAlchemy SQLEnum accepts both enum members and string values
    media = ArticleMedia(
        article_id=article_id,
        type=media_type_value,  # Pass string value directly: "image", "video", or "document"
        key=request.key,
        mime_type=request.mime_type,
        size_bytes=request.size_bytes,
        width=request.width,
        height=request.height,
        duration_seconds=request.duration_seconds,
        url=request.url,
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    
    # Resolve URL
    url = resolve_article_media_url(media, generate_presigned=True)
    
    return ArticleMediaOut(
        id=str(media.id),
        type=get_article_media_type_value(media.type),
        key=media.key,
        url=url,
        mime_type=media.mime_type,
        size_bytes=media.size_bytes,
        width=media.width,
        height=media.height,
        duration_seconds=media.duration_seconds,
        created_at=media.created_at.isoformat(),
    )


@router.get(
    "/articles/{article_id}/media",
    response_model=List[ArticleMediaOut],
    summary="List article media",
    description="List all media items for an article. Requires ADMIN role.",
)
async def list_article_media(
    article_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> List[ArticleMediaOut]:
    """List all media items for an article"""
    # Verify article exists
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ARTICLE_NOT_FOUND"
        )
    
    # Get all media
    media_list = db.query(ArticleMedia).filter(
        ArticleMedia.article_id == article_id
    ).order_by(ArticleMedia.created_at.asc()).all()
    
    result = []
    for media in media_list:
        url = resolve_article_media_url(media, generate_presigned=True)
        result.append(ArticleMediaOut(
            id=str(media.id),
            type=get_article_media_type_value(media.type),
            key=media.key,
            url=url,
            mime_type=media.mime_type,
            size_bytes=media.size_bytes,
            width=media.width,
            height=media.height,
            duration_seconds=media.duration_seconds,
            created_at=media.created_at.isoformat(),
        ))
    
    return result


@router.delete(
    "/articles/{article_id}/media/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete article media",
    description="Delete article media metadata and optionally the S3 object. Requires ADMIN role.",
)
async def delete_article_media(
    article_id: UUID,
    media_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
):
    """Delete article media"""
    # Verify article exists
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ARTICLE_NOT_FOUND"
        )
    
    # Verify media exists and belongs to article
    media = db.query(ArticleMedia).filter(
        ArticleMedia.id == media_id,
        ArticleMedia.article_id == article_id
    ).first()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MEDIA_NOT_FOUND"
        )
    
    # Check if media is used as cover or promo_video
    if article.cover_media_id == media_id:
        article.cover_media_id = None
    if article.promo_video_media_id == media_id:
        article.promo_video_media_id = None
    
    # Delete media record (S3 object deletion is optional and can be done separately)
    db.delete(media)
    db.commit()


@router.post(
    "/articles/{article_id}/media/{media_id}/set-cover",
    response_model=ArticleMediaOut,
    summary="Set article cover image",
    description="Set a media item as the article cover image. Requires ADMIN role.",
)
async def set_article_cover(
    article_id: UUID,
    media_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> ArticleMediaOut:
    """Set article cover image"""
    # Verify article exists
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ARTICLE_NOT_FOUND"
        )
    
    # Verify media exists and belongs to article
    media = db.query(ArticleMedia).filter(
        ArticleMedia.id == media_id,
        ArticleMedia.article_id == article_id,
        ArticleMedia.type == ArticleMediaType.IMAGE  # Cover must be an image
    ).first()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MEDIA_NOT_FOUND_OR_NOT_IMAGE"
        )
    
    # Set as cover
    article.cover_media_id = media_id
    db.commit()
    db.refresh(media)
    
    # Resolve URL
    url = resolve_article_media_url(media, generate_presigned=True)
    
    return ArticleMediaOut(
        id=str(media.id),
        type=get_article_media_type_value(media.type),
        key=media.key,
        url=url,
        mime_type=media.mime_type,
        size_bytes=media.size_bytes,
        width=media.width,
        height=media.height,
        duration_seconds=media.duration_seconds,
        created_at=media.created_at.isoformat(),
    )


@router.post(
    "/articles/{article_id}/media/{media_id}/set-promo-video",
    response_model=ArticleMediaOut,
    summary="Set article promo video",
    description="Set a media item as the article promo video. Requires ADMIN role.",
)
async def set_article_promo_video(
    article_id: UUID,
    media_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> ArticleMediaOut:
    """Set article promo video"""
    # Verify article exists
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ARTICLE_NOT_FOUND"
        )
    
    # Verify media exists and belongs to article
    media = db.query(ArticleMedia).filter(
        ArticleMedia.id == media_id,
        ArticleMedia.article_id == article_id,
        ArticleMedia.type == ArticleMediaType.VIDEO  # Promo video must be a video
    ).first()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MEDIA_NOT_FOUND_OR_NOT_VIDEO"
        )
    
    # Set as promo video
    article.promo_video_media_id = media_id
    db.commit()
    db.refresh(media)
    
    # Resolve URL
    url = resolve_article_media_url(media, generate_presigned=True)
    
    return ArticleMediaOut(
        id=str(media.id),
        type=get_article_media_type_value(media.type),
        key=media.key,
        url=url,
        mime_type=media.mime_type,
        size_bytes=media.size_bytes,
        width=media.width,
        height=media.height,
        duration_seconds=media.duration_seconds,
        created_at=media.created_at.isoformat(),
    )
