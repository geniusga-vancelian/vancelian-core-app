"""
Admin API - Partners management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from uuid import UUID, uuid4
from typing import Optional, List
from datetime import datetime, date

from app.infrastructure.database import get_db
from app.core.partners.models import (
    Partner, PartnerStatus, PartnerTeamMember, PartnerMedia, PartnerMediaType,
    PartnerDocument, PartnerDocumentType, PartnerPortfolioProject,
    PartnerPortfolioProjectStatus, PartnerPortfolioMedia, partner_offers,
)
from app.core.offers.models import Offer
from app.schemas.partners import (
    PartnerCreateIn,
    PartnerUpdateIn,
    PartnerAdminDetail,
    PartnerListItem,
    TeamMemberIn,
    TeamMemberOut,
    PartnerLinkOffersRequest,
    PortfolioProjectCreateIn,
    PortfolioProjectUpdateIn,
    PortfolioProjectOut,
    PortfolioProjectMediaOut,
    PartnerMediaOut,
    PartnerDocumentOut,
    OfferMinimalOut,
)
from app.auth.dependencies import require_admin_role
from app.auth.oidc import Principal
from app.services.storage.s3_service import get_s3_service
from app.services.storage.exceptions import StorageNotConfiguredError

router = APIRouter()


def generate_presigned_url_for_partner_media(media: PartnerMedia) -> Optional[str]:
    """Generate presigned URL for partner media"""
    if media.key:
        try:
            s3_service = get_s3_service()
            return s3_service.generate_presigned_get_url(key=media.key)
        except (StorageNotConfiguredError, Exception):
            return None
    return None


def generate_presigned_url_for_partner_document(doc: PartnerDocument) -> Optional[str]:
    """Generate presigned URL for partner document"""
    if doc.key:
        try:
            s3_service = get_s3_service()
            return s3_service.generate_presigned_get_url(key=doc.key)
        except (StorageNotConfiguredError, Exception):
            return None
    return None


def generate_presigned_url_for_portfolio_media(media: PartnerPortfolioMedia) -> Optional[str]:
    """Generate presigned URL for portfolio media"""
    if media.key:
        try:
            s3_service = get_s3_service()
            return s3_service.generate_presigned_get_url(key=media.key)
        except (StorageNotConfiguredError, Exception):
            return None
    return None


def build_partner_admin_detail(partner: Partner, db: Session) -> PartnerAdminDetail:
    """Build PartnerAdminDetail response with all related data"""
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
    
    # Build portfolio projects
    portfolio_projects_out = []
    for project in partner.portfolio_projects:
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
    
    # Build media list
    media_list = []
    for media in partner.partner_media:
        media_url = generate_presigned_url_for_partner_media(media)
        if media_url:
            media_list.append(PartnerMediaOut(
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
    
    # Build documents list
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
    
    # Build linked offers
    linked_offers = []
    for offer in partner.offers:
        # Check if this is primary
        link = db.execute(
            partner_offers.select().where(
                partner_offers.c.partner_id == partner.id,
                partner_offers.c.offer_id == offer.id
            )
        ).first()
        is_primary = link.is_primary if link else False
        
        linked_offers.append(OfferMinimalOut(
            id=str(offer.id),
            code=offer.code,
            name=offer.name,
            status=offer.status.value,
            is_primary=is_primary,
        ))
    
    return PartnerAdminDetail(
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
        status=partner.status.value,
        ceo_name=partner.ceo_name,
        ceo_title=partner.ceo_title,
        ceo_quote=partner.ceo_quote,
        ceo_bio_markdown=partner.ceo_bio_markdown,
        ceo_photo_media_id=str(partner.ceo_photo_media_id) if partner.ceo_photo_media_id else None,
        ceo_photo_url=ceo_photo_url,
        team_members=team_members_out,
        portfolio_projects=portfolio_projects_out,
        media=media_list,
        documents=documents_list,
        linked_offers=linked_offers,
        created_at=partner.created_at.isoformat(),
        updated_at=partner.updated_at.isoformat() if partner.updated_at else None,
    )


@router.post(
    "/partners",
    response_model=PartnerAdminDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new partner",
    description="Create a new partner in DRAFT status. Requires ADMIN role.",
)
async def create_partner(
    request: PartnerCreateIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> PartnerAdminDetail:
    """Create a new partner"""
    # Check if code already exists
    existing = db.query(Partner).filter(Partner.code == request.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="PARTNER_CODE_EXISTS"
        )
    
    # Create partner
    partner = Partner(
        code=request.code,
        legal_name=request.legal_name,
        trade_name=request.trade_name,
        description_markdown=request.description_markdown,
        website_url=request.website_url,
        address_line1=request.address_line1,
        address_line2=request.address_line2,
        city=request.city,
        country=request.country,
        contact_email=request.contact_email,
        contact_phone=request.contact_phone,
        status=PartnerStatus.DRAFT.value,
        ceo_name=request.ceo_name,
        ceo_title=request.ceo_title,
        ceo_quote=request.ceo_quote,
        ceo_bio_markdown=request.ceo_bio_markdown,
    )
    db.add(partner)
    db.commit()
    db.refresh(partner)
    
    return build_partner_admin_detail(partner, db)


@router.get(
    "/partners",
    response_model=List[PartnerListItem],
    summary="List partners",
    description="List all partners with optional filters. Requires ADMIN role.",
)
async def list_partners(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (DRAFT, PUBLISHED, ARCHIVED)"),
    q: Optional[str] = Query(None, description="Search query (searches legal_name, trade_name, code)"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> List[PartnerListItem]:
    """List partners with filters"""
    query = db.query(Partner)
    
    if status_filter:
        try:
            status_enum = PartnerStatus(status_filter.upper())
            query = query.filter(Partner.status == status_enum.value)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="INVALID_STATUS"
            )
    
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                Partner.legal_name.ilike(search_term),
                Partner.trade_name.ilike(search_term),
                Partner.code.ilike(search_term),
            )
        )
    
    partners = query.order_by(Partner.updated_at.desc().nullslast(), Partner.created_at.desc()).limit(limit).offset(offset).all()
    
    return [
        PartnerListItem(
            id=str(p.id),
            code=p.code,
            legal_name=p.legal_name,
            trade_name=p.trade_name,
            status=p.status.value,
            website_url=p.website_url,
            updated_at=p.updated_at.isoformat() if p.updated_at else None,
        )
        for p in partners
    ]


@router.get(
    "/partners/{partner_id}",
    response_model=PartnerAdminDetail,
    summary="Get partner by ID",
    description="Get partner details. Requires ADMIN role.",
)
async def get_partner(
    partner_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> PartnerAdminDetail:
    """Get partner by ID"""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARTNER_NOT_FOUND"
        )
    
    return build_partner_admin_detail(partner, db)


@router.patch(
    "/partners/{partner_id}",
    response_model=PartnerAdminDetail,
    summary="Update partner",
    description="Update partner fields. Requires ADMIN role.",
)
async def update_partner(
    partner_id: UUID,
    request: PartnerUpdateIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> PartnerAdminDetail:
    """Update partner"""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARTNER_NOT_FOUND"
        )
    
    # Update fields
    if request.code is not None:
        # Check if code is already taken by another partner
        existing = db.query(Partner).filter(Partner.code == request.code, Partner.id != partner_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="PARTNER_CODE_EXISTS"
            )
        partner.code = request.code
    
    if request.legal_name is not None:
        partner.legal_name = request.legal_name
    if request.trade_name is not None:
        partner.trade_name = request.trade_name
    if request.description_markdown is not None:
        partner.description_markdown = request.description_markdown
    if request.website_url is not None:
        partner.website_url = request.website_url
    if request.address_line1 is not None:
        partner.address_line1 = request.address_line1
    if request.address_line2 is not None:
        partner.address_line2 = request.address_line2
    if request.city is not None:
        partner.city = request.city
    if request.country is not None:
        partner.country = request.country
    if request.contact_email is not None:
        partner.contact_email = request.contact_email
    if request.contact_phone is not None:
        partner.contact_phone = request.contact_phone
    if request.status is not None:
        try:
            partner.status = PartnerStatus(request.status.upper()).value
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="INVALID_STATUS"
            )
    
    # CEO module fields
    if request.ceo_name is not None:
        partner.ceo_name = request.ceo_name
    if request.ceo_title is not None:
        partner.ceo_title = request.ceo_title
    if request.ceo_quote is not None:
        partner.ceo_quote = request.ceo_quote
    if request.ceo_bio_markdown is not None:
        partner.ceo_bio_markdown = request.ceo_bio_markdown
    if request.ceo_photo_media_id is not None:
        if request.ceo_photo_media_id:
            try:
                photo_id = UUID(request.ceo_photo_media_id)
                # Verify media exists and belongs to this partner
                photo_media = db.query(PartnerMedia).filter(
                    PartnerMedia.id == photo_id,
                    PartnerMedia.partner_id == partner_id,
                    PartnerMedia.type == PartnerMediaType.IMAGE
                ).first()
                if not photo_media:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="CEO_PHOTO_MEDIA_NOT_FOUND"
                    )
                partner.ceo_photo_media_id = photo_id
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="INVALID_CEO_PHOTO_MEDIA_ID"
                )
        else:
            partner.ceo_photo_media_id = None
    
    db.commit()
    db.refresh(partner)
    
    return build_partner_admin_detail(partner, db)


@router.post(
    "/partners/{partner_id}/publish",
    response_model=PartnerAdminDetail,
    summary="Publish partner",
    description="Set partner status to PUBLISHED. Requires ADMIN role.",
)
async def publish_partner(
    partner_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> PartnerAdminDetail:
    """Publish partner"""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARTNER_NOT_FOUND"
        )
    
    partner.status = PartnerStatus.PUBLISHED.value
    db.commit()
    db.refresh(partner)
    
    return build_partner_admin_detail(partner, db)


@router.post(
    "/partners/{partner_id}/archive",
    response_model=PartnerAdminDetail,
    summary="Archive partner",
    description="Set partner status to ARCHIVED. Requires ADMIN role.",
)
async def archive_partner(
    partner_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> PartnerAdminDetail:
    """Archive partner"""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARTNER_NOT_FOUND"
        )
    
    partner.status = PartnerStatus.ARCHIVED.value
    db.commit()
    db.refresh(partner)
    
    return build_partner_admin_detail(partner, db)


@router.put(
    "/partners/{partner_id}/offers",
    response_model=PartnerAdminDetail,
    summary="Link offers to partner",
    description="Link offers to a partner (primary + additional). Requires ADMIN role.",
)
async def link_partner_offers(
    partner_id: UUID,
    request: PartnerLinkOffersRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> PartnerAdminDetail:
    """Link offers to partner"""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARTNER_NOT_FOUND"
        )
    
    # Clear existing links
    db.execute(
        partner_offers.delete().where(partner_offers.c.partner_id == partner_id)
    )
    
    # Build offer_ids list (include primary if specified)
    offer_ids_to_link = []
    if request.offer_ids:
        offer_ids_to_link = [UUID(oid) for oid in request.offer_ids]
    
    primary_offer_id = None
    if request.primary_offer_id:
        primary_offer_id = UUID(request.primary_offer_id)
        # Ensure primary is in the list
        if primary_offer_id not in offer_ids_to_link:
            offer_ids_to_link.append(primary_offer_id)
    
    # Verify all offers exist
    if offer_ids_to_link:
        existing_offers = db.query(Offer).filter(Offer.id.in_(offer_ids_to_link)).all()
        existing_ids = {offer.id for offer in existing_offers}
        missing_ids = set(offer_ids_to_link) - existing_ids
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OFFERS_NOT_FOUND: {', '.join(str(oid) for oid in missing_ids)}"
            )
    
    # Insert new links
    for offer_id in offer_ids_to_link:
        is_primary = (offer_id == primary_offer_id) if primary_offer_id else False
        db.execute(
            partner_offers.insert().values(
                id=uuid4(),
                partner_id=partner_id,
                offer_id=offer_id,
                is_primary=is_primary,
            )
        )
    
    db.commit()
    db.refresh(partner)
    
    return build_partner_admin_detail(partner, db)

