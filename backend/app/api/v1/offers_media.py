"""
Public API - Offers Media & Documents download
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.infrastructure.database import get_db
from app.core.offers.models import Offer, OfferMedia, OfferDocument, MediaVisibility, DocumentVisibility
from app.schemas.offers import DownloadUrlResponse, MediaItemResponse
from app.auth.dependencies import require_user_role
from app.auth.oidc import Principal
from app.services.storage.s3_service import get_s3_service
from app.services.storage.exceptions import StorageNotConfiguredError
from app.infrastructure.settings import get_settings
from app.utils.trace_id import get_trace_id

router = APIRouter()
settings = get_settings()


def resolve_media_url(media: OfferMedia) -> str | None:
    """Resolve media URL (public CDN or None for presigned)"""
    if media.url:
        return media.url
    if settings.S3_PUBLIC_BASE_URL:
        return f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{media.key}"
    return None


@router.get(
    "/offers/{offer_id}/media",
    response_model=List[MediaItemResponse],
    summary="List offer media (PUBLIC only)",
    description="List all PUBLIC media items for a LIVE offer. Requires USER role.",
)
async def list_offer_media(
    offer_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> List[MediaItemResponse]:
    """List PUBLIC media for an offer"""
    # Verify offer exists and is LIVE
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer or offer.status.value != "LIVE":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Get PUBLIC media only, ordered by sort_order then created_at
    media_list = db.query(OfferMedia).filter(
        OfferMedia.offer_id == offer_id,
        OfferMedia.visibility == MediaVisibility.PUBLIC
    ).order_by(OfferMedia.sort_order.asc(), OfferMedia.created_at.asc()).all()
    
    result = []
    for media in media_list:
        url = resolve_media_url(media)
        result.append(MediaItemResponse(
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
    
    return result


@router.get(
    "/offers/{offer_id}/media/{media_id}/download",
    response_model=DownloadUrlResponse,
    summary="Get presigned download URL for media",
    description="Get a presigned GET URL for downloading a PUBLIC media item. Requires USER role.",
)
async def download_media(
    offer_id: UUID,
    media_id: UUID,
    http_request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> DownloadUrlResponse:
    """Get presigned download URL for media"""
    # Verify offer exists and is LIVE
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer or offer.status.value != "LIVE":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Get media (only PUBLIC)
    media = db.query(OfferMedia).filter(
        OfferMedia.id == media_id,
        OfferMedia.offer_id == offer_id,
        OfferMedia.visibility == MediaVisibility.PUBLIC
    ).first()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MEDIA_NOT_FOUND"
        )
    
    # If media has a public URL, return it (no presigned needed)
    if media.url:
        return DownloadUrlResponse(
            download_url=media.url,
            expires_in=0,  # Public URL doesn't expire
        )
    
    # Generate presigned GET URL
    try:
        s3_service = get_s3_service()
        download_url = s3_service.generate_presigned_get_url(key=media.key)
        
        return DownloadUrlResponse(
            download_url=download_url,
            expires_in=settings.S3_PRESIGN_EXPIRES_SECONDS,
        )
    except StorageNotConfiguredError as e:
        # Storage not configured - return 412 Precondition Failed (consistent with admin endpoints)
        trace_id = get_trace_id(http_request)
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail={
                "code": e.code,
                "message": e.message,
                "trace_id": trace_id,
            }
        )


@router.get(
    "/offers/{offer_id}/documents/{doc_id}/download",
    response_model=DownloadUrlResponse,
    summary="Get presigned download URL for document",
    description="Get a presigned GET URL for downloading a PUBLIC document. Requires USER role.",
)
async def download_document(
    offer_id: UUID,
    doc_id: UUID,
    http_request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> DownloadUrlResponse:
    """Get presigned download URL for document"""
    # Verify offer exists and is LIVE
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer or offer.status.value != "LIVE":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Get document (only PUBLIC)
    doc = db.query(OfferDocument).filter(
        OfferDocument.id == doc_id,
        OfferDocument.offer_id == offer_id,
        OfferDocument.visibility == DocumentVisibility.PUBLIC
    ).first()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DOCUMENT_NOT_FOUND"
        )
    
    # If document has a public URL, return it (no presigned needed)
    if doc.url:
        return DownloadUrlResponse(
            download_url=doc.url,
            expires_in=0,  # Public URL doesn't expire
        )
    
    # Generate presigned GET URL
    try:
        s3_service = get_s3_service()
        download_url = s3_service.generate_presigned_get_url(key=doc.key)
        
        return DownloadUrlResponse(
            download_url=download_url,
            expires_in=settings.S3_PRESIGN_EXPIRES_SECONDS,
        )
    except StorageNotConfiguredError as e:
        # Storage not configured - return 412 Precondition Failed (consistent with admin endpoints)
        trace_id = get_trace_id(http_request)
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail={
                "code": e.code,
                "message": e.message,
                "trace_id": trace_id,
            }
        )
