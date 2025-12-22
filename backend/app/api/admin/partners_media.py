"""
Admin API - Partners Media and Documents management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.infrastructure.database import get_db
from app.core.partners.models import Partner, PartnerMedia, PartnerMediaType, PartnerDocument, PartnerDocumentType, PartnerTeamMember
from app.schemas.partners import (
    PartnerMediaOut, PartnerDocumentOut,
    PartnerPresignUploadRequest, PartnerPresignUploadResponse,
    PartnerCreateMediaRequest, PartnerCreateDocumentRequest
)
from app.auth.dependencies import require_admin_role
from app.auth.oidc import Principal
from app.services.storage.s3_service import get_s3_service
from app.services.storage.exceptions import StorageNotConfiguredError
from app.infrastructure.settings import get_settings
from app.utils.trace_id import get_trace_id

router = APIRouter()
settings = get_settings()


@router.post(
    "/partners/{partner_id}/uploads/presign",
    response_model=PartnerPresignUploadResponse,
    summary="Generate presigned upload URL for partner media/document",
    description="Generate a presigned PUT URL for uploading partner media or document. Requires ADMIN role.",
)
async def presign_partner_upload(
    partner_id: UUID,
    request: PartnerPresignUploadRequest,
    http_request: Request = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> PartnerPresignUploadResponse:
    """Generate presigned upload URL"""
    # Verify partner exists
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARTNER_NOT_FOUND"
        )
    
    # Validate upload type
    if request.upload_type not in ["media", "document"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="INVALID_UPLOAD_TYPE"
        )
    
    if request.upload_type == "media" and not request.media_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MEDIA_TYPE_REQUIRED"
        )
    
    # Get S3 service
    s3_service = get_s3_service()
    
    # Basic size validation
    if request.upload_type == "media":
        max_size = settings.S3_MAX_IMAGE_SIZE if request.media_type == "IMAGE" else settings.S3_MAX_VIDEO_SIZE
    else:
        max_size = settings.S3_MAX_DOCUMENT_SIZE
    
    if request.size_bytes > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size {request.size_bytes} bytes exceeds maximum allowed size {max_size} bytes"
        )
    
    # Build object key
    key = s3_service.build_partner_object_key(partner_id, request.file_name, request.upload_type)
    
    # Generate presigned PUT URL
    try:
        upload_url = s3_service.generate_presigned_put_url(
            key=key,
            mime_type=request.mime_type,
        )
    except StorageNotConfiguredError as e:
        trace_id = get_trace_id(http_request) if http_request else None
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail={
                "code": e.code,
                "message": e.message,
                "trace_id": trace_id,
            }
        )
    except ValueError as e:
        trace_id = get_trace_id(http_request) if http_request else None
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "STORAGE_ERROR",
                "message": str(e),
                "trace_id": trace_id,
            }
        )
    
    return PartnerPresignUploadResponse(
        upload_url=upload_url,
        key=key,
        required_headers={"Content-Type": request.mime_type},
        expires_in=settings.S3_PRESIGN_EXPIRES_SECONDS,
    )


@router.post(
    "/partners/{partner_id}/media",
    response_model=PartnerMediaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create partner media metadata",
    description="Create partner media metadata after successful upload. Requires ADMIN role.",
)
async def create_partner_media(
    partner_id: UUID,
    request: PartnerCreateMediaRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> PartnerMediaOut:
    """Create partner media metadata"""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARTNER_NOT_FOUND"
        )
    
    # Create media record
    media = PartnerMedia(
        partner_id=partner_id,
        type=PartnerMediaType(request.media_type),
        key=request.key,
        mime_type=request.mime_type,
        size_bytes=request.size_bytes,
        width=request.width,
        height=request.height,
        duration_seconds=request.duration_seconds,
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    
    # Generate presigned URL
    url = None
    try:
        s3_service = get_s3_service()
        url = s3_service.generate_presigned_get_url(key=media.key)
    except Exception:
        pass
    
    return PartnerMediaOut(
        id=str(media.id),
        type=media.type.value,
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
    "/partners/{partner_id}/media",
    response_model=List[PartnerMediaOut],
    summary="List partner media",
    description="List all media for a partner. Requires ADMIN role.",
)
async def list_partner_media(
    partner_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> List[PartnerMediaOut]:
    """List partner media"""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARTNER_NOT_FOUND"
        )
    
    media_list = db.query(PartnerMedia).filter(PartnerMedia.partner_id == partner_id).order_by(PartnerMedia.created_at.desc()).all()
    
    results = []
    for media in media_list:
        url = None
        try:
            s3_service = get_s3_service()
            url = s3_service.generate_presigned_get_url(key=media.key)
        except Exception:
            pass
        
        results.append(PartnerMediaOut(
            id=str(media.id),
            type=media.type.value,
            key=media.key,
            url=url,
            mime_type=media.mime_type,
            size_bytes=media.size_bytes,
            width=media.width,
            height=media.height,
            duration_seconds=media.duration_seconds,
            created_at=media.created_at.isoformat(),
        ))
    
    return results


@router.delete(
    "/partners/{partner_id}/media/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete partner media",
    description="Delete partner media. Requires ADMIN role.",
)
async def delete_partner_media(
    partner_id: UUID,
    media_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
):
    """Delete partner media"""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARTNER_NOT_FOUND"
        )
    
    media = db.query(PartnerMedia).filter(
        PartnerMedia.id == media_id,
        PartnerMedia.partner_id == partner_id
    ).first()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MEDIA_NOT_FOUND"
        )
    
    # Check if this media is used as CEO photo or team member photo
    if partner.ceo_photo_media_id == media_id:
        partner.ceo_photo_media_id = None
    
    team_members = db.query(PartnerTeamMember).filter(PartnerTeamMember.photo_media_id == media_id).all()
    for member in team_members:
        member.photo_media_id = None
    
    db.delete(media)
    db.commit()


@router.post(
    "/partners/{partner_id}/documents",
    response_model=PartnerDocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create partner document metadata",
    description="Create partner document metadata after successful upload. Requires ADMIN role.",
)
async def create_partner_document(
    partner_id: UUID,
    request: PartnerCreateDocumentRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> PartnerDocumentOut:
    """Create partner document metadata"""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARTNER_NOT_FOUND"
        )
    
    doc = PartnerDocument(
        partner_id=partner_id,
        title=request.title,
        type=PartnerDocumentType(request.document_type),
        key=request.key,
        mime_type=request.mime_type,
        size_bytes=request.size_bytes,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    # Generate presigned URL
    url = None
    try:
        s3_service = get_s3_service()
        url = s3_service.generate_presigned_get_url(key=doc.key)
    except Exception:
        pass
    
    return PartnerDocumentOut(
        id=str(doc.id),
        title=doc.title,
        type=doc.type.value,
        key=doc.key,
        url=url,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        created_at=doc.created_at.isoformat(),
    )


@router.get(
    "/partners/{partner_id}/documents",
    response_model=List[PartnerDocumentOut],
    summary="List partner documents",
    description="List all documents for a partner. Requires ADMIN role.",
)
async def list_partner_documents(
    partner_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> List[PartnerDocumentOut]:
    """List partner documents"""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARTNER_NOT_FOUND"
        )
    
    docs = db.query(PartnerDocument).filter(PartnerDocument.partner_id == partner_id).order_by(PartnerDocument.created_at.desc()).all()
    
    results = []
    for doc in docs:
        url = None
        try:
            s3_service = get_s3_service()
            url = s3_service.generate_presigned_get_url(key=doc.key)
        except Exception:
            pass
        
        results.append(PartnerDocumentOut(
            id=str(doc.id),
            title=doc.title,
            type=doc.type.value,
            key=doc.key,
            url=url,
            mime_type=doc.mime_type,
            size_bytes=doc.size_bytes,
            created_at=doc.created_at.isoformat(),
        ))
    
    return results


@router.delete(
    "/partners/{partner_id}/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete partner document",
    description="Delete partner document. Requires ADMIN role.",
)
async def delete_partner_document(
    partner_id: UUID,
    doc_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
):
    """Delete partner document"""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARTNER_NOT_FOUND"
        )
    
    doc = db.query(PartnerDocument).filter(
        PartnerDocument.id == doc_id,
        PartnerDocument.partner_id == partner_id
    ).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DOCUMENT_NOT_FOUND"
        )
    
    db.delete(doc)
    db.commit()

