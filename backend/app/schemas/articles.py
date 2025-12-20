"""
Pydantic schemas for Articles API
"""

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List, Dict
from uuid import UUID
import re


# Request schemas (Admin)
class ArticleAdminCreateIn(BaseModel):
    """Request schema for creating an article (admin)"""
    slug: str = Field(..., min_length=3, max_length=255, description="URL-friendly slug (unique)")
    title: str = Field(..., min_length=1, max_length=500, description="Article title")
    subtitle: Optional[str] = Field(None, max_length=500, description="Optional subtitle")
    excerpt: Optional[str] = Field(None, description="Short summary for cards")
    content_markdown: Optional[str] = Field(None, description="Main content in markdown")
    author_name: Optional[str] = Field(None, max_length=255, description="Author name")
    seo_title: Optional[str] = Field(None, max_length=500, description="SEO title (defaults to title if null)")
    seo_description: Optional[str] = Field(None, description="SEO description")
    tags: Optional[List[str]] = Field(default_factory=list, max_length=20, description="Array of tag strings (max 20)")
    is_featured: bool = Field(default=False, description="Featured flag for homepage/blog hero")
    
    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug format: lowercase, alphanumeric, dashes, underscores"""
        if not re.match(r'^[a-z0-9_-]+$', v):
            raise ValueError("Slug must contain only lowercase letters, numbers, dashes, and underscores")
        return v.lower()
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> List[str]:
        """Validate tags: max 20, no empty strings"""
        if v is None:
            return []
        if len(v) > 20:
            raise ValueError("Tags list cannot exceed 20 items")
        # Filter out empty strings
        return [tag.strip() for tag in v if tag.strip()]


class ArticleAdminUpdateIn(BaseModel):
    """Request schema for updating an article (admin)"""
    slug: Optional[str] = Field(None, min_length=3, max_length=255, description="URL-friendly slug (unique)")
    title: Optional[str] = Field(None, min_length=1, max_length=500, description="Article title")
    subtitle: Optional[str] = Field(None, max_length=500, description="Optional subtitle")
    excerpt: Optional[str] = Field(None, description="Short summary for cards")
    content_markdown: Optional[str] = Field(None, description="Main content in markdown")
    content_html: Optional[str] = Field(None, description="Optional pre-rendered HTML")
    author_name: Optional[str] = Field(None, max_length=255, description="Author name")
    seo_title: Optional[str] = Field(None, max_length=500, description="SEO title")
    seo_description: Optional[str] = Field(None, description="SEO description")
    tags: Optional[List[str]] = Field(None, max_length=20, description="Array of tag strings (max 20)")
    is_featured: Optional[bool] = Field(None, description="Featured flag")
    status: Optional[str] = Field(None, pattern="^(draft|published|archived)$", description="Article status")
    
    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        """Validate slug format if provided"""
        if v is None:
            return v
        if not re.match(r'^[a-z0-9_-]+$', v):
            raise ValueError("Slug must contain only lowercase letters, numbers, dashes, and underscores")
        return v.lower()
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate tags if provided"""
        if v is None:
            return v
        if len(v) > 20:
            raise ValueError("Tags list cannot exceed 20 items")
        return [tag.strip() for tag in v if tag.strip()]


class ArticleLinkOffersRequest(BaseModel):
    """Request schema for linking/unlinking offers to/from an article"""
    offer_ids: List[str] = Field(..., description="List of offer IDs (replaces existing links)")


class ArticlePresignUploadRequest(BaseModel):
    """Request for presigned upload URL for article media"""
    upload_type: str = Field(..., description="Upload type: 'image', 'video', or 'document'")
    file_name: str = Field(..., description="Original file name")
    mime_type: str = Field(..., description="MIME type (e.g., image/jpeg, video/mp4, application/pdf)")
    size_bytes: int = Field(..., gt=0, description="File size in bytes")


class ArticlePresignUploadResponse(BaseModel):
    """Response with presigned upload URL for article media"""
    upload_url: str = Field(..., description="Presigned PUT URL for uploading")
    key: str = Field(..., description="S3 object key to use")
    required_headers: Dict[str, str] = Field(..., description="Required headers for upload (at least Content-Type)")
    expires_in: int = Field(..., description="Expiration time in seconds")


class ArticleCreateMediaRequest(BaseModel):
    """Request to create article media metadata after upload"""
    key: str = Field(..., description="S3 object key (from presign response)")
    mime_type: str = Field(..., description="MIME type")
    size_bytes: int = Field(..., gt=0, description="File size in bytes")
    type: str = Field(..., description="Media type: 'image', 'video', or 'document'")
    url: Optional[str] = Field(None, description="Optional public CDN URL")
    width: Optional[int] = Field(None, ge=1, description="Image/video width in pixels")
    height: Optional[int] = Field(None, ge=1, description="Image/video height in pixels")
    duration_seconds: Optional[int] = Field(None, ge=0, description="Video duration in seconds")


# Media schemas (similar to OfferMedia)
class ArticleMediaOut(BaseModel):
    """Article media response schema"""
    id: str = Field(..., description="Media UUID")
    type: str = Field(..., description="Media type: 'image', 'video', or 'document'")
    key: str = Field(..., description="S3/R2 object key")
    url: Optional[str] = Field(None, description="Resolved URL (public CDN or presigned)")
    mime_type: str = Field(..., description="MIME type")
    size_bytes: int = Field(..., description="File size in bytes")
    width: Optional[int] = Field(None, description="Width in pixels")
    height: Optional[int] = Field(None, description="Height in pixels")
    duration_seconds: Optional[int] = Field(None, description="Duration in seconds (for videos)")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    
    class Config:
        from_attributes = True


class PresignedArticleMediaItemResponse(BaseModel):
    """Article media item with presigned URL for public API"""
    id: str = Field(..., description="Media UUID")
    type: str = Field(..., description="Media type: 'image', 'video', or 'document'")
    kind: Optional[str] = Field(None, description="Media kind: 'cover' or 'promo_video' (for gallery items, kind is None)")
    url: str = Field(..., description="Presigned URL (always generated, never None)")
    mime_type: str = Field(..., description="MIME type")
    size_bytes: int = Field(..., description="File size in bytes")
    width: Optional[int] = Field(None, description="Width in pixels")
    height: Optional[int] = Field(None, description="Height in pixels")
    duration_seconds: Optional[int] = Field(None, description="Duration in seconds (for videos)")


class ArticleMediaBlockResponse(BaseModel):
    """Structured media block for public API responses"""
    cover: Optional[PresignedArticleMediaItemResponse] = Field(None, description="Cover image with presigned URL")
    promo_video: Optional[PresignedArticleMediaItemResponse] = Field(None, description="Promo video with presigned URL")
    gallery: List[PresignedArticleMediaItemResponse] = Field(default_factory=list, description="Gallery images/videos (excluding cover and promo_video)")
    documents: List[PresignedArticleMediaItemResponse] = Field(default_factory=list, description="Document files with presigned URLs")


# Response schemas (Public)
class ArticlePublicListItem(BaseModel):
    """Article list item (public) - minimal fields for cards"""
    id: str = Field(..., description="Article UUID")
    slug: str = Field(..., description="URL-friendly slug")
    title: str = Field(..., description="Article title")
    subtitle: Optional[str] = Field(None, description="Optional subtitle")
    excerpt: Optional[str] = Field(None, description="Short summary")
    cover_url: Optional[str] = Field(None, description="Cover image URL (presigned)")
    author_name: Optional[str] = Field(None, description="Author name")
    published_at: Optional[str] = Field(None, description="Publication timestamp (ISO format)")
    tags: List[str] = Field(default_factory=list, description="Tags list")
    is_featured: bool = Field(default=False, description="Featured flag")
    
    class Config:
        from_attributes = True


class OfferMinimalResponse(BaseModel):
    """Minimal offer info for article detail"""
    id: str = Field(..., description="Offer UUID")
    code: str = Field(..., description="Offer code")
    name: str = Field(..., description="Offer name")
    
    class Config:
        from_attributes = True


class ArticlePublicDetail(BaseModel):
    """Article detail response (public)"""
    id: str = Field(..., description="Article UUID")
    slug: str = Field(..., description="URL-friendly slug")
    title: str = Field(..., description="Article title")
    subtitle: Optional[str] = Field(None, description="Optional subtitle")
    excerpt: Optional[str] = Field(None, description="Short summary")
    content_markdown: Optional[str] = Field(None, description="Main content in markdown")
    content_html: Optional[str] = Field(None, description="Pre-rendered HTML (if available)")
    author_name: Optional[str] = Field(None, description="Author name")
    published_at: Optional[str] = Field(None, description="Publication timestamp (ISO format)")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    updated_at: Optional[str] = Field(None, description="Last update timestamp (ISO format)")
    tags: List[str] = Field(default_factory=list, description="Tags list")
    is_featured: bool = Field(default=False, description="Featured flag")
    media: Optional[ArticleMediaBlockResponse] = Field(None, description="Structured media block with presigned URLs")
    offers: List[OfferMinimalResponse] = Field(default_factory=list, description="Linked offers (minimal info)")
    seo_title: Optional[str] = Field(None, description="SEO title")
    seo_description: Optional[str] = Field(None, description="SEO description")
    
    class Config:
        from_attributes = True


# Response schemas (Admin)
class ArticleAdminListItem(BaseModel):
    """Article list item (admin) - includes status"""
    id: str = Field(..., description="Article UUID")
    slug: str = Field(..., description="URL-friendly slug")
    title: str = Field(..., description="Article title")
    status: str = Field(..., description="Status: draft, published, or archived")
    published_at: Optional[str] = Field(None, description="Publication timestamp (ISO format)")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    updated_at: Optional[str] = Field(None, description="Last update timestamp (ISO format)")
    is_featured: bool = Field(default=False, description="Featured flag")
    
    class Config:
        from_attributes = True


class ArticleAdminDetail(BaseModel):
    """Article detail response (admin)"""
    id: str = Field(..., description="Article UUID")
    slug: str = Field(..., description="URL-friendly slug")
    status: str = Field(..., description="Status: draft, published, or archived")
    title: str = Field(..., description="Article title")
    subtitle: Optional[str] = Field(None, description="Optional subtitle")
    excerpt: Optional[str] = Field(None, description="Short summary")
    content_markdown: Optional[str] = Field(None, description="Main content in markdown")
    content_html: Optional[str] = Field(None, description="Pre-rendered HTML")
    cover_media_id: Optional[str] = Field(None, description="Cover media ID")
    promo_video_media_id: Optional[str] = Field(None, description="Promo video media ID")
    author_name: Optional[str] = Field(None, description="Author name")
    published_at: Optional[str] = Field(None, description="Publication timestamp (ISO format)")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    updated_at: Optional[str] = Field(None, description="Last update timestamp (ISO format)")
    seo_title: Optional[str] = Field(None, description="SEO title")
    seo_description: Optional[str] = Field(None, description="SEO description")
    tags: List[str] = Field(default_factory=list, description="Tags list")
    is_featured: bool = Field(default=False, description="Featured flag")
    allow_comments: bool = Field(default=False, description="Comments flag")
    media: List[ArticleMediaOut] = Field(default_factory=list, description="All media attached to this article")
    offer_ids: List[str] = Field(default_factory=list, description="Linked offer IDs")
    
    class Config:
        from_attributes = True

