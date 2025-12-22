"""
Public API - Partners (Trusted Partners)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from uuid import UUID
from typing import Optional, List
import logging

from app.infrastructure.database import get_db
from app.core.partners.models import (
    Partner, PartnerStatus, PartnerTeamMember, PartnerMedia, PartnerMediaType,
    PartnerDocument, PartnerPortfolioProject, PartnerPortfolioProjectStatus,
    PartnerPortfolioMedia, partner_offers,
)
from app.core.offers.models import Offer
from app.schemas.partners import (
    PublicPartnerListItem,
    PublicPartnerDetail,
    PartnerMediaOut,
    PartnerDocumentOut,
    TeamMemberOut,
    PortfolioProjectOut,
    PortfolioProjectMediaOut,
    OfferMinimalOut,
)
from app.services.storage.s3_service import get_s3_service
from app.services.storage.exceptions import StorageNotConfiguredError

logger = logging.getLogger(__name__)

router = APIRouter()


def generate_presigned_url_for_partner_media(media: PartnerMedia) -> Optional[str]:
    """Generate presigned URL for partner media"""
    try:
        s3_service = get_s3_service()
        return s3_service.generate_presigned_get_url(key=media.key)
    except (StorageNotConfiguredError, Exception) as e:
        logger.warning(f"Cannot generate presigned URL for partner media {media.id}: {str(e)}")
        return None


def generate_presigned_url_for_partner_document(doc: PartnerDocument) -> Optional[str]:
    """Generate presigned URL for partner document"""
    try:
        s3_service = get_s3_service()
        return s3_service.generate_presigned_get_url(key=doc.key)
    except (StorageNotConfiguredError, Exception) as e:
        logger.warning(f"Cannot generate presigned URL for partner document {doc.id}: {str(e)}")
        return None


def generate_presigned_url_for_portfolio_media(media: PartnerPortfolioMedia) -> Optional[str]:
    """Generate presigned URL for portfolio media"""
    try:
        s3_service = get_s3_service()
        return s3_service.generate_presigned_get_url(key=media.key)
    except (StorageNotConfiguredError, Exception) as e:
        logger.warning(f"Cannot generate presigned URL for portfolio media {media.id}: {str(e)}")
        return None


@router.get(
    "/partners",
    response_model=List[PublicPartnerListItem],
    summary="List published partners",
    description="List all published partners (for directory).",
)
async def list_partners(
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
) -> List[PublicPartnerListItem]:
    """List published partners"""
    partners = db.query(Partner).filter(
        Partner.status == PartnerStatus.PUBLISHED.value
    ).order_by(Partner.created_at.desc()).limit(limit).offset(offset).all()
    
    results = []
    for partner in partners:
        # Get CEO photo URL
        ceo_photo_url = None
        if partner.ceo_photo_media_id:
            ceo_photo_media = db.query(PartnerMedia).filter(PartnerMedia.id == partner.ceo_photo_media_id).first()
            if ceo_photo_media:
                ceo_photo_url = generate_presigned_url_for_partner_media(ceo_photo_media)
        
        # Get first gallery image as cover (or CEO photo)
        cover_image_url = ceo_photo_url
        if not cover_image_url:
            first_image = db.query(PartnerMedia).filter(
                PartnerMedia.partner_id == partner.id,
                PartnerMedia.type == PartnerMediaType.IMAGE
            ).first()
            if first_image:
                cover_image_url = generate_presigned_url_for_partner_media(first_image)
        
        results.append(PublicPartnerListItem(
            id=str(partner.id),
            code=partner.code,
            trade_name=partner.trade_name,
            legal_name=partner.legal_name,
            description_markdown=partner.description_markdown,
            website_url=partner.website_url,
            city=partner.city,
            country=partner.country,
            ceo_name=partner.ceo_name,
            ceo_photo_url=ceo_photo_url,
            cover_image_url=cover_image_url,
        ))
    
    return results


@router.get(
    "/partners/{code_or_id}",
    response_model=PublicPartnerDetail,
    summary="Get partner by code or ID",
    description="Get partner details (PUBLISHED only).",
)
async def get_partner(
    code_or_id: str,
    db: Session = Depends(get_db),
) -> PublicPartnerDetail:
    """Get partner by code or ID (PUBLISHED only)"""
    # Try to parse as UUID first
    partner = None
    try:
        partner_id = UUID(code_or_id)
        partner = db.query(Partner).filter(
            Partner.id == partner_id,
            Partner.status == PartnerStatus.PUBLISHED.value
        ).first()
    except ValueError:
        # Not a UUID, try as code
        partner = db.query(Partner).filter(
            Partner.code == code_or_id,
            Partner.status == PartnerStatus.PUBLISHED.value
        ).first()
    
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARTNER_NOT_FOUND"
        )
    
    # Get CEO photo URL
    ceo_photo_url = None
    if partner.ceo_photo_media_id:
        ceo_photo_media = db.query(PartnerMedia).filter(PartnerMedia.id == partner.ceo_photo_media_id).first()
        if ceo_photo_media:
            ceo_photo_url = generate_presigned_url_for_partner_media(ceo_photo_media)
    
    # Build team members
    team_members_out = []
    for member in partner.team_members:
        photo_url = None
        if member.photo_media_id:
            photo_media = db.query(PartnerMedia).filter(PartnerMedia.id == member.photo_media_id).first()
            if photo_media:
                photo_url = generate_presigned_url_for_partner_media(photo_media)
        
        team_members_out.append(TeamMemberOut(
            id=str(member.id),
            full_name=member.full_name,
            role_title=member.role_title,
            bio_markdown=member.bio_markdown,
            linkedin_url=member.linkedin_url,
            website_url=member.website_url,
            photo_media_id=str(member.photo_media_id) if member.photo_media_id else None,
            photo_url=photo_url,
            sort_order=member.sort_order,
            created_at=member.created_at.isoformat(),
            updated_at=member.updated_at.isoformat() if member.updated_at else None,
        ))
    
    # Build portfolio projects (PUBLISHED only)
    portfolio_projects_out = []
    for project in partner.portfolio_projects:
        if project.status != PartnerPortfolioProjectStatus.PUBLISHED.value:
            continue
        
        # Get cover and promo video URLs
        cover_url = None
        promo_video_url = None
        gallery = []
        
        for media in project.portfolio_media:
            media_url = generate_presigned_url_for_portfolio_media(media)
            if media_url:
                if media.id == project.cover_media_id:
                    cover_url = media_url
                elif media.id == project.promo_video_media_id:
                    promo_video_url = media_url
                else:
                    # Gallery item
                    gallery.append(PortfolioProjectMediaOut(
                        id=str(media.id),
                        type=media.type.value,
                        key=media.key,
                        url=media_url,
                        mime_type=media.mime_type,
                        size_bytes=media.size_bytes,
                        width=media.width,
                        height=media.height,
                        duration_seconds=media.duration_seconds,
                        created_at=media.created_at.isoformat(),
                    ))
        
        portfolio_projects_out.append(PortfolioProjectOut(
            id=str(project.id),
            title=project.title,
            category=project.category,
            location=project.location,
            start_date=project.start_date.isoformat() if project.start_date else None,
            end_date=project.end_date.isoformat() if project.end_date else None,
            short_summary=project.short_summary,
            description_markdown=project.description_markdown,
            results_kpis=project.results_kpis if project.results_kpis else [],
            status=project.status.value,
            cover_media_id=str(project.cover_media_id) if project.cover_media_id else None,
            cover_url=cover_url,
            promo_video_media_id=str(project.promo_video_media_id) if project.promo_video_media_id else None,
            promo_video_url=promo_video_url,
            gallery=gallery,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat() if project.updated_at else None,
        ))
    
    # Build gallery (images only, excluding promo video)
    gallery = []
    promo_video = None
    for media in partner.partner_media:
        if media.type == PartnerMediaType.VIDEO:
            # Only one promo video (first one found)
            if promo_video is None:
                media_url = generate_presigned_url_for_partner_media(media)
                if media_url:
                    promo_video = PartnerMediaOut(
                        id=str(media.id),
                        type=media.type.value,
                        key=media.key,
                        url=media_url,
                        mime_type=media.mime_type,
                        size_bytes=media.size_bytes,
                        width=media.width,
                        height=media.height,
                        duration_seconds=media.duration_seconds,
                        created_at=media.created_at.isoformat(),
                    )
        else:
            # Image (exclude CEO photo from gallery)
            if media.id != partner.ceo_photo_media_id:
                media_url = generate_presigned_url_for_partner_media(media)
                if media_url:
                    gallery.append(PartnerMediaOut(
                        id=str(media.id),
                        type=media.type.value,
                        key=media.key,
                        url=media_url,
                        mime_type=media.mime_type,
                        size_bytes=media.size_bytes,
                        width=media.width,
                        height=media.height,
                        duration_seconds=media.duration_seconds,
                        created_at=media.created_at.isoformat(),
                    ))
    
    # Build documents
    documents_list = []
    for doc in partner.partner_documents:
        doc_url = generate_presigned_url_for_partner_document(doc)
        if doc_url:
            documents_list.append(PartnerDocumentOut(
                id=str(doc.id),
                title=doc.title,
                type=doc.type.value,
                key=doc.key,
                url=doc_url,
                mime_type=doc.mime_type,
                size_bytes=doc.size_bytes,
                created_at=doc.created_at.isoformat(),
            ))
    
    # Build related offers (PUBLISHED partners only, and only LIVE offers)
    related_offers = []
    for offer in partner.offers:
        if offer.status.value == "LIVE":  # Only show LIVE offers
            # Check if this is primary
            link = db.execute(
                partner_offers.select().where(
                    partner_offers.c.partner_id == partner.id,
                    partner_offers.c.offer_id == offer.id
                )
            ).first()
            is_primary = link.is_primary if link else False
            
            related_offers.append(OfferMinimalOut(
                id=str(offer.id),
                code=offer.code,
                name=offer.name,
                status=offer.status.value,
                is_primary=is_primary,
            ))
    
    # Sort: primary first
    related_offers.sort(key=lambda x: (not x.is_primary, x.code))
    
    return PublicPartnerDetail(
        id=str(partner.id),
        code=partner.code,
        legal_name=partner.legal_name,
        trade_name=partner.trade_name,
        description_markdown=partner.description_markdown,
        website_url=partner.website_url,
        address_line1=partner.address_line1,
        address_line2=partner.address_line2,
        city=partner.city,
        country=partner.country,
        contact_email=partner.contact_email,
        contact_phone=partner.contact_phone,
        ceo_name=partner.ceo_name,
        ceo_title=partner.ceo_title,
        ceo_quote=partner.ceo_quote,
        ceo_bio_markdown=partner.ceo_bio_markdown,
        ceo_photo_url=ceo_photo_url,
        team_members=team_members_out,
        portfolio_projects=portfolio_projects_out,
        gallery=gallery,
        promo_video=promo_video,
        documents=documents_list,
        related_offers=related_offers,
    )


@router.get(
    "/offers/{offer_id}/partners",
    response_model=List[PublicPartnerListItem],
    summary="Get partners linked to an offer",
    description="List published partners linked to a specific offer (primary first).",
)
async def get_offer_partners(
    offer_id: UUID,
    limit: int = Query(default=10, ge=1, le=50, description="Maximum number of results"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
) -> List[PublicPartnerListItem]:
    """Get published partners linked to an offer"""
    # Verify offer exists
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OFFER_NOT_FOUND"
        )
    
    # Get partners linked to this offer (PUBLISHED only)
    partners = db.query(Partner).join(partner_offers).filter(
        partner_offers.c.offer_id == offer_id,
        Partner.status == PartnerStatus.PUBLISHED.value
    ).order_by(
        partner_offers.c.is_primary.desc(),  # Primary first
        Partner.created_at.desc()
    ).limit(limit).offset(offset).all()
    
    results = []
    for partner in partners:
        # Get CEO photo URL
        ceo_photo_url = None
        if partner.ceo_photo_media_id:
            ceo_photo_media = db.query(PartnerMedia).filter(PartnerMedia.id == partner.ceo_photo_media_id).first()
            if ceo_photo_media:
                ceo_photo_url = generate_presigned_url_for_partner_media(ceo_photo_media)
        
        # Get first gallery image as cover (or CEO photo)
        cover_image_url = ceo_photo_url
        if not cover_image_url:
            first_image = db.query(PartnerMedia).filter(
                PartnerMedia.partner_id == partner.id,
                PartnerMedia.type == PartnerMediaType.IMAGE
            ).first()
            if first_image:
                cover_image_url = generate_presigned_url_for_partner_media(first_image)
        
        results.append(PublicPartnerListItem(
            id=str(partner.id),
            code=partner.code,
            trade_name=partner.trade_name,
            legal_name=partner.legal_name,
            description_markdown=partner.description_markdown,
            website_url=partner.website_url,
            city=partner.city,
            country=partner.country,
            ceo_name=partner.ceo_name,
            ceo_photo_url=ceo_photo_url,
            cover_image_url=cover_image_url,
        ))
    
    return results

