"""
Investment API request/response schemas
"""

from decimal import Decimal
from uuid import UUID
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class CreateInvestmentRequest(BaseModel):
    """Request schema for creating investment intent"""
    amount: Decimal = Field(..., description="Investment amount (must be <= available balance)")
    currency: str = Field(default="AED", description="Currency code (default: AED)")
    offer_id: UUID = Field(..., description="Investment offer UUID")
    reason: str = Field(..., min_length=1, description="Investment reason (e.g., 'Investment in Exclusive Offer X')")

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Ensure amount is positive"""
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Normalize currency to uppercase"""
        return v.upper()

    class Config:
        json_schema_extra = {
            "example": {
                "amount": "5000.00",
                "currency": "AED",
                "offer_id": "123e4567-e89b-12d3-a456-426614174000",
                "reason": "Investment in Exclusive Offer X",
            }
        }


class CreateInvestmentResponse(BaseModel):
    """Response schema for investment creation"""
    transaction_id: str = Field(..., description="Transaction UUID")
    status: str = Field(..., description="Transaction status (should be LOCKED after funds locked)")

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "LOCKED",
            }
        }


# Investment Offer Schemas

from datetime import datetime
from typing import Dict, Any


class CreateOfferRequest(BaseModel):
    """Request schema for creating an investment offer (admin only)"""
    product_code: str = Field(..., min_length=1, max_length=50, description="Unique product code (e.g. 'EXCL_RE_001')")
    title: str = Field(..., min_length=1, max_length=255, description="Offer title")
    description: Optional[str] = Field(None, description="Offer description")
    currency: str = Field(default="AED", description="Currency code (default: AED)")
    total_capacity: Decimal = Field(..., gt=0, description="Maximum amount that can be raised")
    min_ticket: Optional[Decimal] = Field(None, gt=0, description="Minimum investment ticket size")
    max_ticket: Optional[Decimal] = Field(None, gt=0, description="Maximum investment ticket size")
    maturity_date: Optional[datetime] = Field(None, description="Maturity date (timestamptz, optional)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata (JSONB)")

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Normalize currency to uppercase"""
        return v.upper()
    
    @field_validator('max_ticket')
    @classmethod
    def validate_max_ticket(cls, v: Optional[Decimal], info) -> Optional[Decimal]:
        """Ensure max_ticket >= min_ticket if both are provided"""
        if v is not None and 'min_ticket' in info.data and info.data['min_ticket'] is not None:
            if v < info.data['min_ticket']:
                raise ValueError("max_ticket must be >= min_ticket")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "product_code": "EXCL_RE_001",
                "title": "Exclusive Real Estate Fund Q1 2025",
                "description": "Premium real estate investment opportunity",
                "currency": "AED",
                "total_capacity": "1000000.00",
                "min_ticket": "10000.00",
                "max_ticket": "100000.00",
                "maturity_date": "2026-12-31T23:59:59Z",
                "metadata": {"sector": "real_estate", "region": "UAE"},
            }
        }


class UpdateOfferRequest(BaseModel):
    """Request schema for updating an investment offer (admin only)"""
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Offer title")
    description: Optional[str] = Field(None, description="Offer description")
    total_capacity: Optional[Decimal] = Field(None, gt=0, description="Maximum amount that can be raised")
    min_ticket: Optional[Decimal] = Field(None, gt=0, description="Minimum investment ticket size")
    max_ticket: Optional[Decimal] = Field(None, gt=0, description="Maximum investment ticket size")
    maturity_date: Optional[datetime] = Field(None, description="Maturity date (timestamptz, optional)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata (JSONB)")

    @field_validator('max_ticket')
    @classmethod
    def validate_max_ticket(cls, v: Optional[Decimal], info) -> Optional[Decimal]:
        """Ensure max_ticket >= min_ticket if both are provided"""
        if v is not None and 'min_ticket' in info.data and info.data['min_ticket'] is not None:
            if v < info.data['min_ticket']:
                raise ValueError("max_ticket must be >= min_ticket")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Updated Exclusive Real Estate Fund Q1 2025",
                "description": "Updated description",
                "total_capacity": "2000000.00",
                "min_ticket": "20000.00",
                "max_ticket": "200000.00",
            }
        }


class OfferResponse(BaseModel):
    """Response schema for investment offer"""
    id: str = Field(..., description="Offer UUID")
    product_code: str = Field(..., description="Unique product code")
    title: str = Field(..., description="Offer title")
    description: Optional[str] = Field(None, description="Offer description")
    currency: str = Field(..., description="Currency code")
    status: str = Field(..., description="Offer status (DRAFT, OPEN, CLOSED)")
    total_capacity: str = Field(..., description="Maximum amount that can be raised")
    allocated_amount: str = Field(..., description="Current amount allocated")
    min_ticket: Optional[str] = Field(None, description="Minimum investment ticket size")
    max_ticket: Optional[str] = Field(None, description="Maximum investment ticket size")
    maturity_date: Optional[str] = Field(None, description="Maturity date (ISO format)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    updated_at: Optional[str] = Field(None, description="Last update timestamp (ISO format)")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "product_code": "EXCL_RE_001",
                "title": "Exclusive Real Estate Fund Q1 2025",
                "description": "Premium real estate investment opportunity",
                "currency": "AED",
                "status": "OPEN",
                "total_capacity": "1000000.00",
                "allocated_amount": "500000.00",
                "min_ticket": "10000.00",
                "max_ticket": "100000.00",
                "maturity_date": "2026-12-31T23:59:59Z",
                "metadata": {"sector": "real_estate", "region": "UAE"},
                "created_at": "2025-12-19T00:00:00Z",
                "updated_at": "2025-12-19T01:00:00Z",
            }
        }


class OfferListItem(BaseModel):
    """Response schema for offer list item (simplified)"""
    id: str = Field(..., description="Offer UUID")
    product_code: str = Field(..., description="Unique product code")
    title: str = Field(..., description="Offer title")
    currency: str = Field(..., description="Currency code")
    status: str = Field(..., description="Offer status")
    total_capacity: str = Field(..., description="Maximum amount that can be raised")
    allocated_amount: str = Field(..., description="Current amount allocated")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")


class InvestRequest(BaseModel):
    """Request schema for investing in an offer"""
    requested_amount: Decimal = Field(..., gt=0, description="Requested investment amount")

    @field_validator('requested_amount')
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Ensure amount is positive"""
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "requested_amount": "10000.00",
            }
        }


class InvestResponse(BaseModel):
    """Response schema for investment intent"""
    intent_id: str = Field(..., description="Investment intent UUID")
    offer_id: str = Field(..., description="Offer UUID")
    requested_amount: str = Field(..., description="Requested investment amount")
    allocated_amount: str = Field(..., description="Actually allocated amount (may be less if offer is near total_capacity)")
    status: str = Field(..., description="Intent status (ACTIVE if allocated > 0, FAILED otherwise)")
    offer_status: str = Field(..., description="Offer status after investment (may be CLOSED if total_capacity reached)")

    class Config:
        json_schema_extra = {
            "example": {
                "intent_id": "123e4567-e89b-12d3-a456-426614174000",
                "offer_id": "456e7890-e89b-12d3-a456-426614174000",
                "requested_amount": "10000.00",
                "allocated_amount": "10000.00",
                "status": "ACTIVE",
                "offer_status": "OPEN",
            }
        }



