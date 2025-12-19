"""
Pydantic schemas for Offers API
"""

from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, Any
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

    class Config:
        from_attributes = True


class OfferInvestmentResponse(BaseModel):
    investment_id: str = Field(..., description="Investment UUID")
    offer_id: str = Field(..., description="Offer UUID")
    requested_amount: str = Field(..., description="Requested investment amount")
    accepted_amount: str = Field(..., description="Accepted investment amount (may be less than requested)")
    currency: str = Field(..., description="Currency code")
    status: str = Field(..., description="Investment status (PENDING, ACCEPTED, REJECTED)")
    offer_committed_amount: str = Field(..., description="Total committed amount in offer after this investment")
    offer_remaining_amount: str = Field(..., description="Remaining capacity in offer after this investment")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")

    class Config:
        from_attributes = True

