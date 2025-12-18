"""
Webhook payload schemas
"""

from decimal import Decimal
from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ZandDepositWebhookPayload(BaseModel):
    """
    ZAND Bank deposit webhook payload schema
    
    Expected payload from ZAND Bank for AED deposits.
    """
    provider_event_id: str = Field(..., description="Unique event ID from ZAND Bank")
    iban: str = Field(..., description="IBAN identifier")
    user_id: UUID = Field(..., description="User UUID (mapped from IBAN)")
    amount: Decimal = Field(..., description="Deposit amount")
    currency: str = Field(..., description="Currency code (must be AED)")
    occurred_at: datetime = Field(..., description="Timestamp when deposit occurred")

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
        """Ensure currency is AED"""
        if v.upper() != "AED":
            raise ValueError("Currency must be AED")
        return v.upper()

    class Config:
        json_schema_extra = {
            "example": {
                "provider_event_id": "ZAND-EVT-123456789",
                "iban": "AE123456789012345678901",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "amount": "1000.00",
                "currency": "AED",
                "occurred_at": "2025-12-18T10:00:00Z",
            }
        }


class ZandDepositWebhookResponse(BaseModel):
    """Webhook response schema"""
    status: str = Field(..., description="Processing status (accepted, duplicate, etc.)")
    transaction_id: str = Field(..., description="Transaction UUID")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "accepted",
                "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
            }
        }



