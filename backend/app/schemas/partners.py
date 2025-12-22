"""
Pydantic schemas for Partners API
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from uuid import UUID


# ============ Request Schemas (Admin) ============

class PartnerCreateIn(BaseModel):
    """Request schema for creating a partner (admin)"""
    code: str = Field(..., min_length=3, max_length=100, description="Unique slug-like code")
    legal_name: str = Field(..., min_length=1, max_length=255, description="Legal name")
    trade_name: Optional[str] = Field(None, max_length=255, description="Trade name (optional)")
    description_markdown: Optional[str] = Field(None, description="Description in markdown")
    website_url: Optional[str] = Field(None, max_length=500, description="Website URL")
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    
    # CEO module
    ceo_name: Optional[str] = Field(None, max_length=255)
    ceo_title: Optional[str] = Field(None, max_length=255)
    ceo_quote: Optional[str] = Field(None, max_length=240, description="CEO quote (max 240 chars)")
    ceo_bio_markdown: Optional[str] = Field(None, description="CEO bio in markdown")


class PartnerUpdateIn(BaseModel):
    """Request schema for updating a partner (admin)"""
    code: Optional[str] = Field(None, min_length=3, max_length=100)
    legal_name: Optional[str] = Field(None, min_length=1, max_length=255)
    trade_name: Optional[str] = Field(None, max_length=255)
    description_markdown: Optional[str] = Field(None)
    website_url: Optional[str] = Field(None, max_length=500)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, pattern="^(DRAFT|PUBLISHED|ARCHIVED)$")
    
    # CEO module
    ceo_name: Optional[str] = Field(None, max_length=255)
    ceo_title: Optional[str] = Field(None, max_length=255)
    ceo_quote: Optional[str] = Field(None, max_length=240)
    ceo_bio_markdown: Optional[str] = Field(None)
    ceo_photo_media_id: Optional[str] = Field(None, description="CEO photo media ID")
    
    @field_validator('ceo_quote')
    @classmethod
    def validate_ceo_quote(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 240:
            raise ValueError("CEO quote cannot exceed 240 characters")
        return v


class TeamMemberIn(BaseModel):
    """Request schema for team member (create/update)"""
    id: Optional[str] = Field(None, description="ID for update (omit for create)")
    full_name: str = Field(..., min_length=1, max_length=255)
    role_title: Optional[str] = Field(None, max_length=255)
    bio_markdown: Optional[str] = Field(None)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    website_url: Optional[str] = Field(None, max_length=500)
    photo_media_id: Optional[str] = Field(None, description="Photo media ID")
    sort_order: Optional[int] = Field(0, ge=0)


class PartnerLinkOffersRequest(BaseModel):
    """Request schema for linking offers to a partner"""
    primary_offer_id: Optional[str] = Field(None, description="Primary offer ID (optional)")
    offer_ids: Optional[List[str]] = Field(None, description="List of offer IDs (replaces existing links)")
    
    @field_validator('offer_ids')
    @classmethod
    def validate_offer_ids(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            # Remove duplicates
            seen = set()
            unique_list = []
            for item in v:
                if item not in seen:
                    seen.add(item)
                    unique_list.append(item)
            return unique_list
        return v


class PortfolioProjectCreateIn(BaseModel):
    """Request schema for creating a portfolio project"""
    title: str = Field(..., min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=255)
    start_date: Optional[str] = Field(None, description="Start date (ISO format: YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (ISO format: YYYY-MM-DD)")
    short_summary: Optional[str] = Field(None, max_length=240, description="Short summary (max 240 chars)")
    description_markdown: Optional[str] = Field(None)
    results_kpis: Optional[List[str]] = Field(None, max_length=12, description="List of KPI strings (max 12, each max 40 chars)")
    status: Optional[str] = Field("DRAFT", pattern="^(DRAFT|PUBLISHED|ARCHIVED)$")
    
    @field_validator('short_summary')
    @classmethod
    def validate_short_summary(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 240:
            raise ValueError("Short summary cannot exceed 240 characters")
        return v
    
    @field_validator('results_kpis')
    @classmethod
    def validate_results_kpis(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            if len(v) > 12:
                raise ValueError("Results KPIs list cannot exceed 12 items")
            for kpi in v:
                if len(kpi) > 40:
                    raise ValueError(f"KPI '{kpi}' cannot exceed 40 characters")
        return v


class PortfolioProjectUpdateIn(BaseModel):
    """Request schema for updating a portfolio project"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=255)
    start_date: Optional[str] = Field(None)
    end_date: Optional[str] = Field(None)
    short_summary: Optional[str] = Field(None, max_length=240)
    description_markdown: Optional[str] = Field(None)
    results_kpis: Optional[List[str]] = Field(None, max_length=12)
    status: Optional[str] = Field(None, pattern="^(DRAFT|PUBLISHED|ARCHIVED)$")
    cover_media_id: Optional[str] = Field(None)
    promo_video_media_id: Optional[str] = Field(None)
    
    @field_validator('short_summary', 'results_kpis')
    @classmethod
    def validate_fields(cls, v, info):
        if info.field_name == 'short_summary' and v is not None and len(v) > 240:
            raise ValueError("Short summary cannot exceed 240 characters")
        if info.field_name == 'results_kpis' and v is not None:
            if len(v) > 12:
                raise ValueError("Results KPIs list cannot exceed 12 items")
            for kpi in v:
                if len(kpi) > 40:
                    raise ValueError(f"KPI '{kpi}' cannot exceed 40 characters")
        return v


# ============ Request Schemas (Media) ============

class PartnerPresignUploadRequest(BaseModel):
    """Request for presigned upload URL for partner media/document"""
    upload_type: str = Field(..., description="Upload type: 'media' or 'document'")
    file_name: str = Field(..., description="Original file name")
    mime_type: str = Field(..., description="MIME type (e.g., image/jpeg, video/mp4, application/pdf)")
    size_bytes: int = Field(..., gt=0, description="File size in bytes")
    media_type: Optional[str] = Field(None, description="Media type: 'IMAGE' or 'VIDEO' (required if upload_type='media')")


class PartnerPresignUploadResponse(BaseModel):
    """Response with presigned upload URL for partner media/document"""
    upload_url: str = Field(..., description="Presigned PUT URL for uploading")
    key: str = Field(..., description="S3 object key to use")
    required_headers: dict = Field(..., description="Required headers for upload (at least Content-Type)")
    expires_in: int = Field(..., description="Expiration time in seconds")


class PartnerCreateMediaRequest(BaseModel):
    """Request to create partner media metadata after upload"""
    key: str = Field(..., description="S3 object key (from presign response)")
    mime_type: str = Field(..., description="MIME type")
    size_bytes: int = Field(..., gt=0, description="File size in bytes")
    media_type: str = Field(..., description="Media type: 'IMAGE' or 'VIDEO'")
    width: Optional[int] = Field(None, ge=1, description="Image/video width in pixels")
    height: Optional[int] = Field(None, ge=1, description="Image/video height in pixels")
    duration_seconds: Optional[int] = Field(None, ge=0, description="Video duration in seconds")


class PartnerCreateDocumentRequest(BaseModel):
    """Request to create partner document metadata after upload"""
    title: str = Field(..., min_length=1, max_length=255, description="Document title")
    key: str = Field(..., description="S3 object key (from presign response)")
    mime_type: str = Field(..., description="MIME type")
    size_bytes: int = Field(..., gt=0, description="File size in bytes")
    document_type: str = Field(..., description="Document type: 'PDF', 'DOC', or 'OTHER'")


# ============ Response Schemas ============

class PartnerMediaOut(BaseModel):
    """Partner media response"""
    id: str
    type: str  # "IMAGE" | "VIDEO"
    key: str
    url: Optional[str] = None  # Presigned URL or public URL
    mime_type: str
    size_bytes: int
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[int] = None
    created_at: str


class PartnerDocumentOut(BaseModel):
    """Partner document response"""
    id: str
    title: str
    type: str  # "PDF" | "DOC" | "OTHER"
    key: str
    url: Optional[str] = None  # Presigned URL
    mime_type: str
    size_bytes: int
    created_at: str


class TeamMemberOut(BaseModel):
    """Team member response"""
    id: str
    full_name: str
    role_title: Optional[str] = None
    bio_markdown: Optional[str] = None
    linkedin_url: Optional[str] = None
    website_url: Optional[str] = None
    photo_media_id: Optional[str] = None
    photo_url: Optional[str] = None  # Presigned URL
    sort_order: int
    created_at: str
    updated_at: Optional[str] = None


class PortfolioProjectMediaOut(BaseModel):
    """Portfolio project media response"""
    id: str
    type: str  # "IMAGE" | "VIDEO"
    key: str
    url: Optional[str] = None
    mime_type: str
    size_bytes: int
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[int] = None
    created_at: str


class PortfolioProjectOut(BaseModel):
    """Portfolio project response"""
    id: str
    title: str
    category: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    short_summary: Optional[str] = None
    description_markdown: Optional[str] = None
    results_kpis: Optional[List[str]] = None
    status: str
    cover_media_id: Optional[str] = None
    cover_url: Optional[str] = None
    promo_video_media_id: Optional[str] = None
    promo_video_url: Optional[str] = None
    gallery: List[PortfolioProjectMediaOut] = []
    created_at: str
    updated_at: Optional[str] = None


class OfferMinimalOut(BaseModel):
    """Minimal offer info for partner response"""
    id: str
    code: str
    name: str
    status: str
    is_primary: bool = False


class PartnerAdminDetail(BaseModel):
    """Admin partner detail response"""
    id: str
    code: str
    legal_name: str
    trade_name: Optional[str] = None
    description_markdown: Optional[str] = None
    website_url: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    status: str
    ceo_name: Optional[str] = None
    ceo_title: Optional[str] = None
    ceo_quote: Optional[str] = None
    ceo_bio_markdown: Optional[str] = None
    ceo_photo_media_id: Optional[str] = None
    ceo_photo_url: Optional[str] = None
    team_members: List[TeamMemberOut] = []
    portfolio_projects: List[PortfolioProjectOut] = []
    media: List[PartnerMediaOut] = []
    documents: List[PartnerDocumentOut] = []
    linked_offers: List[OfferMinimalOut] = []
    created_at: str
    updated_at: Optional[str] = None


class PartnerListItem(BaseModel):
    """Partner list item (admin)"""
    id: str
    code: str
    legal_name: str
    trade_name: Optional[str] = None
    status: str
    website_url: Optional[str] = None
    updated_at: Optional[str] = None


# ============ Public Response Schemas ============

class PublicPartnerListItem(BaseModel):
    """Public partner list item (for directory)"""
    id: str
    code: str
    trade_name: Optional[str] = None
    legal_name: str
    description_markdown: Optional[str] = None
    website_url: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    ceo_name: Optional[str] = None
    ceo_photo_url: Optional[str] = None
    cover_image_url: Optional[str] = None  # First gallery image or CEO photo


class PublicPartnerDetail(BaseModel):
    """Public partner detail response"""
    id: str
    code: str
    legal_name: str
    trade_name: Optional[str] = None
    description_markdown: Optional[str] = None
    website_url: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    
    # CEO module
    ceo_name: Optional[str] = None
    ceo_title: Optional[str] = None
    ceo_quote: Optional[str] = None
    ceo_bio_markdown: Optional[str] = None
    ceo_photo_url: Optional[str] = None
    
    # Team (published only - empty for now, could filter if needed)
    team_members: List[TeamMemberOut] = []
    
    # Portfolio (published projects only)
    portfolio_projects: List[PortfolioProjectOut] = []
    
    # Media
    gallery: List[PartnerMediaOut] = []  # Images only
    promo_video: Optional[PartnerMediaOut] = None  # If present
    
    # Documents
    documents: List[PartnerDocumentOut] = []
    
    # Related offers (PUBLISHED partners only)
    related_offers: List[OfferMinimalOut] = []

