"""
Admin API - Offers Media & Documents management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional

from app.infrastructure.database import get_db
from app.core.offers.models import (
    Offer, OfferMedia, OfferDocument,
    MediaType, MediaVisibility, DocumentKind, DocumentVisibility
)
from app.schemas.offers import (
    PresignUploadRequest, PresignUploadResponse,
    CreateMediaRequest, CreateDocumentRequest,
    MediaItemResponse, DocumentItemResponse,
    ReorderMediaRequest, DownloadUrlResponse,
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


def resolve_media_url(media: OfferMedia, generate_presigned: bool = False) -> Optional[str]:
    """Resolve media URL (public CDN, presigned, or None)
    
    Args:
        media: OfferMedia object
        generate_presigned: If True and no public URL exists, generate a presigned GET URL
    """
    if media.url:
        return media.url
    if settings.S3_PUBLIC_BASE_URL:
        return f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{media.key}"
    if generate_presigned:
        try:
            s3_service = get_s3_service()
            return s3_service.generate_presigned_get_url(key=media.key)
        except (StorageNotConfiguredError, Exception):
            # If storage not configured or error, return None
            return None
    return None


def resolve_document_url(doc: OfferDocument) -> Optional[str]:
    """Resolve document URL (public CDN or None for presigned)"""
    if doc.url:
        return doc.url
    if settings.S3_PUBLIC_BASE_URL:
        return f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{doc.key}"
    return None


@router.post(
    "/offers/{offer_id}/uploads/presign",
    response_model=PresignUploadResponse,
    summary="Generate presigned upload URL",
    description="Generate a presigned PUT URL for uploading media or documents. Requires ADMIN role.",
)
async def presign_upload(
    offer_id: UUID,
    request: PresignUploadRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> PresignUploadResponse:
    """Generate presigned upload URL"""
    # Verify offer exists
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Validate upload type
    if request.upload_type not in ["media", "document"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="INVALID_UPLOAD_TYPE"
        )
    
    # Get S3 service
    s3_service = get_s3_service()
    
    # Validate MIME type and size
    try:
        s3_service.validate_mime_type(
            request.mime_type,
            request.upload_type,
            request.media_type
        )
        s3_service.validate_size(
            request.size_bytes,
            request.upload_type,
            request.media_type
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Build object key
    key = s3_service.build_object_key(offer_id, request.file_name, request.upload_type)
    
    # Generate presigned PUT URL
    try:
        upload_url = s3_service.generate_presigned_put_url(
            key=key,
            mime_type=request.mime_type,
        )
    except StorageNotConfiguredError as e:
        # Storage not configured - return 412 Precondition Failed
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
    
    return PresignUploadResponse(
        upload_url=upload_url,
        key=key,
        required_headers={"Content-Type": request.mime_type},
        expires_in=settings.S3_PRESIGN_EXPIRES_SECONDS,
    )


@router.post(
    "/offers/{offer_id}/media",
    response_model=MediaItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create media metadata",
    description="Create media metadata after successful upload. Requires ADMIN role.",
)
async def create_media(
    offer_id: UUID,
    request: CreateMediaRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> MediaItemResponse:
    """Create media metadata after upload"""
    # Verify offer exists
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Validate media type
    try:
        media_type = MediaType[request.type.upper()]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid media type: {request.type}. Expected IMAGE or VIDEO"
        )
    
    # Validate visibility
    try:
        visibility = MediaVisibility[request.visibility.upper()]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid visibility: {request.visibility}. Expected PUBLIC or PRIVATE"
        )
    
    # Enforce: only one VIDEO per offer
    if media_type == MediaType.VIDEO:
        existing_video = db.query(OfferMedia).filter(
            OfferMedia.offer_id == offer_id,
            OfferMedia.type == MediaType.VIDEO
        ).first()
        if existing_video:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="OFFER_VIDEO_ALREADY_EXISTS: Only one promo video is allowed per offer. Delete the existing video first."
            )
    
    # If this is set as cover, unset other covers
    if request.is_cover:
        db.query(OfferMedia).filter(
            OfferMedia.offer_id == offer_id,
            OfferMedia.is_cover == True
        ).update({"is_cover": False})
    
    # Create media record
    media = OfferMedia(
        offer_id=offer_id,
        type=media_type,
        key=request.key,
        url=request.url,
        mime_type=request.mime_type,
        size_bytes=request.size_bytes,
        width=request.width,
        height=request.height,
        duration_seconds=request.duration_seconds,
        sort_order=request.sort_order,
        is_cover=request.is_cover,
        visibility=visibility,
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    
    # Resolve URL (generate presigned if no public URL)
    url = resolve_media_url(media, generate_presigned=True)
    
    return MediaItemResponse(
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
    )


@router.post(
    "/offers/{offer_id}/documents",
    response_model=DocumentItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create document metadata",
    description="Create document metadata after successful upload. Requires ADMIN role.",
)
async def create_document(
    offer_id: UUID,
    request: CreateDocumentRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> DocumentItemResponse:
    """Create document metadata after upload"""
    # Verify offer exists
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Validate document kind
    try:
        kind = DocumentKind[request.kind.upper()]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document kind: {request.kind}"
        )
    
    # Validate visibility
    try:
        visibility = DocumentVisibility[request.visibility.upper()]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid visibility: {request.visibility}. Expected PUBLIC or PRIVATE"
        )
    
    # Create document record
    doc = OfferDocument(
        offer_id=offer_id,
        name=request.name,
        kind=kind,
        key=request.key,
        mime_type=request.mime_type,
        size_bytes=request.size_bytes,
        visibility=visibility,
        url=request.url,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    # Resolve URL
    url = resolve_document_url(doc)
    
    return DocumentItemResponse(
        id=str(doc.id),
        name=doc.name,
        kind=doc.kind.value,
        url=url,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        created_at=doc.created_at.isoformat(),
    )


@router.get(
    "/offers/{offer_id}/media",
    response_model=List[MediaItemResponse],
    summary="List offer media",
    description="List all media items for an offer. Requires ADMIN role.",
)
async def list_media(
    offer_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> List[MediaItemResponse]:
    """List all media items for an offer"""
    # Verify offer exists
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Get all media (admin sees all, including PRIVATE)
    media_list = db.query(OfferMedia).filter(
        OfferMedia.offer_id == offer_id
    ).order_by(OfferMedia.sort_order.asc(), OfferMedia.created_at.asc()).all()
    
    result = []
    for media in media_list:
        url = resolve_media_url(media, generate_presigned=True)
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
    "/offers/{offer_id}/documents",
    response_model=List[DocumentItemResponse],
    summary="List offer documents",
    description="List all documents for an offer. Requires ADMIN role.",
)
async def list_documents(
    offer_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> List[DocumentItemResponse]:
    """List all documents for an offer"""
    # Verify offer exists
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Get all documents (admin sees all, including PRIVATE)
    docs = db.query(OfferDocument).filter(
        OfferDocument.offer_id == offer_id
    ).order_by(OfferDocument.created_at.desc()).all()
    
    result = []
    for doc in docs:
        url = resolve_document_url(doc)
        result.append(DocumentItemResponse(
            id=str(doc.id),
            name=doc.name,
            kind=doc.kind.value,
            url=url,
            mime_type=doc.mime_type,
            size_bytes=doc.size_bytes,
            created_at=doc.created_at.isoformat(),
        ))
    
    return result


@router.patch(
    "/offers/{offer_id}/media/reorder",
    response_model=List[MediaItemResponse],
    summary="Reorder media items",
    description="Update sort_order and is_cover for media items. Requires ADMIN role.",
)
async def reorder_media(
    offer_id: UUID,
    request: ReorderMediaRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> List[MediaItemResponse]:
    """Reorder media items"""
    # Verify offer exists
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Update each media item
    for item in request.items:
        media_id = UUID(item["id"])
        media = db.query(OfferMedia).filter(
            OfferMedia.id == media_id,
            OfferMedia.offer_id == offer_id
        ).first()
        
        if not media:
            continue  # Skip invalid IDs
        
        media.sort_order = item.get("sort_order", media.sort_order)
        if "is_cover" in item:
            # If setting as cover, unset others
            if item["is_cover"]:
                db.query(OfferMedia).filter(
                    OfferMedia.offer_id == offer_id,
                    OfferMedia.is_cover == True,
                    OfferMedia.id != media_id
                ).update({"is_cover": False})
            media.is_cover = item["is_cover"]
    
    db.commit()
    
    # Return updated list
    return await list_media(offer_id, db, principal)


@router.delete(
    "/offers/{offer_id}/media/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete media item",
    description="Delete a media item (metadata only; S3 object not deleted). Requires ADMIN role.",
)
async def delete_media(
    offer_id: UUID,
    media_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
):
    """Delete media item"""
    # Verify offer exists
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Find and delete media
    media = db.query(OfferMedia).filter(
        OfferMedia.id == media_id,
        OfferMedia.offer_id == offer_id
    ).first()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MEDIA_NOT_FOUND"
        )
    
    # If this media is used as cover or promo, nullify those references first
    if offer.cover_media_id == media_id:
        offer.cover_media_id = None
    if offer.promo_video_media_id == media_id:
        offer.promo_video_media_id = None
    
    db.delete(media)
    db.commit()
    
    return None


@router.delete(
    "/offers/{offer_id}/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete document",
    description="Delete a document (metadata only; S3 object not deleted). Requires ADMIN role.",
)
async def delete_document(
    offer_id: UUID,
    doc_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
):
    """Delete document"""
    # Verify offer exists
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Find and delete document
    doc = db.query(OfferDocument).filter(
        OfferDocument.id == doc_id,
        OfferDocument.offer_id == offer_id
    ).first()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DOCUMENT_NOT_FOUND"
        )
    
    db.delete(doc)
    db.commit()
    
    return None

