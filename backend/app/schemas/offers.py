"""
Pydantic schemas for Offers API
"""

from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID


# Request schemas
class CreateOfferRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50, description="Unique offer code (e.g. 'NEST-ALBARARI-001')")
    name: str = Field(..., min_length=1, max_length=255, description="Offer name")
    description: Optional[str] = Field(None, description="Offer description")
    currency: str = Field(default="AED", min_length=3, max_length=3, description="Currency code (default: AED)")
    max_amount: Decimal = Field(..., gt=0, description="Maximum amount that can be committed")
    maturity_date: Optional[datetime] = Field(None, description="Maturity date (ISO format)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Arbitrary metadata (JSONB)")


class UpdateOfferRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Offer name")
    description: Optional[str] = Field(None, description="Offer description")
    max_amount: Optional[Decimal] = Field(None, gt=0, description="Maximum amount that can be committed")
    maturity_date: Optional[datetime] = Field(None, description="Maturity date (ISO format)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Arbitrary metadata (JSONB)")


class InvestInOfferRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Amount to invest")
    currency: str = Field(default="AED", min_length=3, max_length=3, description="Currency code")
    idempotency_key: Optional[str] = Field(None, max_length=255, description="Idempotency key to prevent duplicate investments")


# Media/Documents schemas (defined before OfferResponse to avoid forward reference)
class MediaItemResponse(BaseModel):
    """Media item response (for public and admin)"""
    id: str = Field(..., description="Media UUID")
    type: str = Field(..., description="Media type: 'IMAGE' or 'VIDEO'")
    url: Optional[str] = Field(None, description="Resolved URL (public CDN or presigned)")
    mime_type: str = Field(..., description="MIME type")
    size_bytes: int = Field(..., description="File size in bytes")
    sort_order: int = Field(..., description="Sort order")
    is_cover: bool = Field(..., description="Is cover image?")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    width: Optional[int] = Field(None, description="Width in pixels")
    height: Optional[int] = Field(None, description="Height in pixels")
    duration_seconds: Optional[int] = Field(None, description="Duration in seconds (for videos)")

    class Config:
        from_attributes = True


class DocumentItemResponse(BaseModel):
    """Document item response (for public and admin)"""
    id: str = Field(..., description="Document UUID")
    name: str = Field(..., description="Document name")
    kind: str = Field(..., description="Document kind")
    url: Optional[str] = Field(None, description="Resolved URL (public CDN or presigned)")
    mime_type: str = Field(..., description="MIME type")
    size_bytes: int = Field(..., description="File size in bytes")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")

    class Config:
        from_attributes = True


# Response schemas
class OfferResponse(BaseModel):
    id: str = Field(..., description="Offer UUID")
    code: str = Field(..., description="Unique offer code")
    name: str = Field(..., description="Offer name")
    description: Optional[str] = Field(None, description="Offer description")
    currency: str = Field(..., description="Currency code")
    max_amount: str = Field(..., description="Maximum amount that can be committed")
    committed_amount: str = Field(..., description="Current committed amount")
    remaining_amount: str = Field(..., description="Remaining capacity (max_amount - committed_amount)")
    maturity_date: Optional[str] = Field(None, description="Maturity date (ISO format)")
    status: str = Field(..., description="Offer status (DRAFT, LIVE, PAUSED, CLOSED)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Arbitrary metadata (JSONB)")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    updated_at: Optional[str] = Field(None, description="Last update timestamp (ISO format)")
    media: Optional[List[MediaItemResponse]] = Field(default=[], description="Public media items (PUBLIC visibility only)")
    documents: Optional[List[DocumentItemResponse]] = Field(default=[], description="Public documents (PUBLIC visibility only)")

    class Config:
        from_attributes = True


class OfferInvestmentResponse(BaseModel):
    investment_id: str = Field(..., description="Investment UUID")
    offer_id: str = Field(..., description="Offer UUID")
    requested_amount: str = Field(..., description="Requested investment amount")
    accepted_amount: str = Field(..., description="Accepted investment amount (may be less than requested)")
    currency: str = Field(..., description="Currency code")
    status: str = Field(..., description="Investment status (PENDING, CONFIRMED, REJECTED) - v1.1")
    offer_committed_amount: str = Field(..., description="Total committed amount in offer after this investment")
    offer_remaining_amount: str = Field(..., description="Remaining capacity in offer after this investment")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")

    class Config:
        from_attributes = True


class OfferInvestmentListItem(BaseModel):
    """Admin view of an investment intent for an offer"""
    id: str = Field(..., description="Investment Intent UUID")
    offer_id: str = Field(..., description="Offer UUID")
    user_id: str = Field(..., description="User UUID")
    user_email: str = Field(..., description="User email address")
    requested_amount: str = Field(..., description="Requested investment amount")
    allocated_amount: str = Field(..., description="Allocated investment amount (may be less than requested)")
    currency: str = Field(..., description="Currency code")
    status: str = Field(..., description="Investment Intent status (PENDING, CONFIRMED, REJECTED)")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    updated_at: Optional[str] = Field(None, description="Last update timestamp (ISO format)")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key")

    class Config:
        from_attributes = True


class OfferInvestmentsPaginatedResponse(BaseModel):
    """Paginated response for offer investments list"""
    items: List[OfferInvestmentListItem] = Field(..., description="List of investment intents")
    limit: int = Field(..., description="Maximum number of results per page")
    offset: int = Field(..., description="Number of results skipped")
    total: int = Field(..., description="Total number of investment intents matching the filter")

    class Config:
        from_attributes = True


# Media/Documents schemas
class PresignUploadRequest(BaseModel):
    """Request for presigned upload URL"""
    upload_type: str = Field(..., description="Upload type: 'media' or 'document'")
    file_name: str = Field(..., description="Original file name")
    mime_type: str = Field(..., description="MIME type (e.g., image/jpeg, application/pdf)")
    size_bytes: int = Field(..., gt=0, description="File size in bytes")
    media_type: Optional[str] = Field(None, description="Media type: 'IMAGE' or 'VIDEO' (required if upload_type='media')")
    document_kind: Optional[str] = Field(None, description="Document kind: 'BROCHURE', 'MEMO', etc. (required if upload_type='document')")


class PresignUploadResponse(BaseModel):
    """Response with presigned upload URL"""
    upload_url: str = Field(..., description="Presigned PUT URL for uploading")
    key: str = Field(..., description="S3 object key to use")
    required_headers: Dict[str, str] = Field(..., description="Required headers for upload (at least Content-Type)")
    expires_in: int = Field(..., description="Expiration time in seconds")


class CreateMediaRequest(BaseModel):
    """Request to create media metadata after upload"""
    key: str = Field(..., description="S3 object key (from presign response)")
    mime_type: str = Field(..., description="MIME type")
    size_bytes: int = Field(..., gt=0, description="File size in bytes")
    type: str = Field(..., description="Media type: 'IMAGE' or 'VIDEO'")
    sort_order: Optional[int] = Field(0, ge=0, description="Sort order (default: 0)")
    is_cover: Optional[bool] = Field(False, description="Is this the cover image? (default: false)")
    visibility: Optional[str] = Field("PUBLIC", description="Visibility: 'PUBLIC' or 'PRIVATE' (default: PUBLIC)")
    url: Optional[str] = Field(None, description="Optional public CDN URL")
    width: Optional[int] = Field(None, ge=1, description="Image/video width in pixels")
    height: Optional[int] = Field(None, ge=1, description="Image/video height in pixels")
    duration_seconds: Optional[int] = Field(None, ge=0, description="Video duration in seconds")


class CreateDocumentRequest(BaseModel):
    """Request to create document metadata after upload"""
    name: str = Field(..., min_length=1, max_length=255, description="Document name")
    kind: str = Field(..., description="Document kind: 'BROCHURE', 'MEMO', 'PROJECTIONS', 'VALUATION', 'OTHER'")
    key: str = Field(..., description="S3 object key (from presign response)")
    mime_type: str = Field(..., description="MIME type")
    size_bytes: int = Field(..., gt=0, description="File size in bytes")
    visibility: Optional[str] = Field("PUBLIC", description="Visibility: 'PUBLIC' or 'PRIVATE' (default: PUBLIC)")
    url: Optional[str] = Field(None, description="Optional public CDN URL")


class ReorderMediaRequest(BaseModel):
    """Request to reorder media items"""
    items: List[Dict[str, Any]] = Field(..., description="List of {id, sort_order, is_cover?}")


class DownloadUrlResponse(BaseModel):
    """Response with presigned download URL"""
    download_url: str = Field(..., description="Presigned GET URL")
    expires_in: int = Field(..., description="Expiration time in seconds")

