"""
Pydantic schemas for Offer Timeline Events
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator
from uuid import UUID


class TimelineEventArticleInfo(BaseModel):
    """Article information linked to a timeline event"""
    id: str = Field(..., description="Article ID")
    title: str = Field(..., description="Article title")
    slug: str = Field(..., description="Article slug")
    published_at: Optional[str] = Field(None, description="Published date (ISO format)")
    cover_url: Optional[str] = Field(None, description="Cover image URL (presigned)")


class TimelineEventResponse(BaseModel):
    """Timeline event response (public and admin)"""
    id: str = Field(..., description="Event ID")
    title: str = Field(..., description="Event title")
    description: str = Field(..., description="Event description")
    occurred_at: Optional[str] = Field(None, description="When the event occurred (ISO format)")
    sort_order: int = Field(..., description="Display order")
    article: Optional[TimelineEventArticleInfo] = Field(None, description="Linked article (if any)")
    created_at: str = Field(..., description="Creation date (ISO format)")
    updated_at: Optional[str] = Field(None, description="Last update date (ISO format)")


class TimelineEventCreateIn(BaseModel):
    """Request schema for creating a timeline event"""
    title: str = Field(..., min_length=1, max_length=120, description="Event title (max 120 chars)")
    description: str = Field(..., min_length=1, max_length=280, description="Event description (max 280 chars)")
    occurred_at: Optional[str] = Field(None, description="When the event occurred (ISO format, optional)")
    article_id: Optional[str] = Field(None, description="Optional article ID to link")
    sort_order: Optional[int] = Field(0, ge=0, description="Display order (default 0)")
    
    @validator('title')
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()
    
    @validator('description')
    def validate_description(cls, v):
        if not v or not v.strip():
            raise ValueError('Description cannot be empty')
        return v.strip()


class TimelineEventUpdateIn(BaseModel):
    """Request schema for updating a timeline event"""
    title: Optional[str] = Field(None, min_length=1, max_length=120, description="Event title")
    description: Optional[str] = Field(None, min_length=1, max_length=280, description="Event description")
    occurred_at: Optional[str] = Field(None, description="When the event occurred (ISO format)")
    article_id: Optional[str] = Field(None, description="Article ID to link (null to unlink)")
    sort_order: Optional[int] = Field(None, ge=0, description="Display order")
    
    @validator('title')
    def validate_title(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Title cannot be empty')
        return v.strip() if v else None
    
    @validator('description')
    def validate_description(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Description cannot be empty')
        return v.strip() if v else None


class TimelineReorderItem(BaseModel):
    """Item for reordering timeline events"""
    id: str = Field(..., description="Event ID")
    sort_order: int = Field(..., ge=0, description="New sort order")


class TimelineReorderIn(BaseModel):
    """Request schema for reordering timeline events"""
    items: List[TimelineReorderItem] = Field(..., min_items=1, description="List of events with new sort orders")
    
    @validator('items')
    def validate_unique_ids(cls, v):
        ids = [item.id for item in v]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate event IDs in reorder request')
        return v
    
    @validator('items')
    def validate_unique_orders(cls, v):
        orders = [item.sort_order for item in v]
        if len(orders) != len(set(orders)):
            raise ValueError('Duplicate sort orders in reorder request')
        return v

