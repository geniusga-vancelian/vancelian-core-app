"""
Investment API request/response schemas
"""

from decimal import Decimal
from uuid import UUID
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

