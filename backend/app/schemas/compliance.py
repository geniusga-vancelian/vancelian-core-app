"""
Compliance API request/response schemas
"""

from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class ReleaseFundsRequest(BaseModel):
    """Request schema for releasing compliance-blocked funds"""
    transaction_id: UUID = Field(..., description="Transaction UUID")
    amount: Decimal = Field(..., description="Amount to release (must be <= blocked balance)")
    reason: str = Field(..., min_length=1, description="Mandatory reason for release (audit trail)")

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Ensure amount is positive"""
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
                "amount": "10000.00",
                "reason": "AML review completed - no suspicious activity detected",
            }
        }


class ReleaseFundsResponse(BaseModel):
    """Response schema for release funds operation"""
    transaction_id: str = Field(..., description="Transaction UUID")
    status: str = Field(..., description="New transaction status (should be AVAILABLE)")

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "AVAILABLE",
            }
        }


class RejectDepositRequest(BaseModel):
    """Request schema for rejecting a deposit"""
    transaction_id: UUID = Field(..., description="Transaction UUID")
    reason: str = Field(..., min_length=1, description="Mandatory reason for rejection (audit trail)")

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
                "reason": "Sanctions match / invalid IBAN",
            }
        }


class RejectDepositResponse(BaseModel):
    """Response schema for reject deposit operation"""
    transaction_id: str = Field(..., description="Transaction UUID")
    status: str = Field(..., description="New transaction status (should be FAILED)")

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "FAILED",
            }
        }
