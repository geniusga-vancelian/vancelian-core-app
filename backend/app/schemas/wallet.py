"""
Wallet API response schemas
"""

from pydantic import BaseModel, Field


class WalletBalanceResponse(BaseModel):
    """Wallet balance response schema"""
    currency: str = Field(..., description="ISO 4217 currency code (e.g., AED)")
    total_balance: str = Field(..., description="Total wallet balance (sum of all compartments)")
    available_balance: str = Field(..., description="Available balance (WALLET_AVAILABLE compartment)")
    blocked_balance: str = Field(..., description="Blocked balance (WALLET_BLOCKED compartment)")
    locked_balance: str = Field(..., description="Locked balance (WALLET_LOCKED compartment)")

    class Config:
        json_schema_extra = {
            "example": {
                "currency": "AED",
                "total_balance": "10000.00",
                "available_balance": "7000.00",
                "blocked_balance": "2000.00",
                "locked_balance": "1000.00",
            }
        }


class TransactionListItem(BaseModel):
    """Transaction list item response schema"""
    transaction_id: str | None = Field(None, description="Transaction UUID (if linked to Transaction)")
    operation_id: str | None = Field(None, description="Operation UUID (primary operation)")
    type: str = Field(..., description="Transaction type (DEPOSIT, WITHDRAWAL, INVESTMENT) or Operation type")
    operation_type: str | None = Field(None, description="Operation type (DEPOSIT_AED, INVEST_EXCLUSIVE, etc.)")
    status: str = Field(..., description="Transaction status or Operation status")
    amount: str = Field(..., description="Transaction amount (absolute value for INVESTMENT, net for others)")
    currency: str = Field(..., description="ISO 4217 currency code (e.g., AED)")
    created_at: str = Field(..., description="ISO 8601 timestamp")
    metadata: dict | None = Field(None, description="Metadata (offer_id, offer_code, offer_name, etc.)")
    offer_product: str | None = Field(None, description="Offer/product name for display (derived from metadata)")

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
                "operation_id": "123e4567-e89b-12d3-a456-426614174001",
                "type": "DEPOSIT",
                "operation_type": "DEPOSIT_AED",
                "status": "AVAILABLE",
                "amount": "10000.00",
                "currency": "AED",
                "created_at": "2025-12-18T00:00:00Z",
                "metadata": {"offer_id": "123e4567-e89b-12d3-a456-426614174002", "offer_code": "NEST-001", "offer_name": "Al Barari"},
                "offer_product": "Al Barari (NEST-001)",
            }
        }


class WalletMovement(BaseModel):
    """Wallet movement (from bucket to bucket)"""
    from_bucket: str = Field(..., description="Source wallet bucket (e.g., AVAILABLE, UNDER_REVIEW, LOCKED)")
    to_bucket: str = Field(..., description="Destination wallet bucket (e.g., AVAILABLE, LOCKED)")


class TransactionDetailResponse(BaseModel):
    """Transaction detail response schema"""
    id: str = Field(..., description="Transaction UUID")
    type: str = Field(..., description="Transaction type (DEPOSIT, WITHDRAWAL, INVESTMENT)")
    status: str = Field(..., description="Transaction status")
    amount: str = Field(..., description="Transaction amount")
    currency: str = Field(..., description="ISO 4217 currency code")
    created_at: str = Field(..., description="ISO 8601 timestamp")
    updated_at: str | None = Field(None, description="ISO 8601 timestamp (if available)")
    metadata: dict | None = Field(None, description="Transaction metadata")
    trace_id: str | None = Field(None, description="Trace ID for debugging")
    user_email: str | None = Field(None, description="User email (if available)")
    operation_id: str | None = Field(None, description="Primary operation ID")
    operation_type: str | None = Field(None, description="Primary operation type")
    movement: WalletMovement | None = Field(None, description="Wallet movement (from/to buckets)")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "type": "INVESTMENT",
                "status": "LOCKED",
                "amount": "2000.00",
                "currency": "AED",
                "created_at": "2025-12-19T15:53:38Z",
                "updated_at": "2025-12-19T15:54:10Z",
                "metadata": {"offer_id": "...", "offer_code": "NEST-001", "offer_name": "Al Barari"},
                "trace_id": "trace-123",
                "user_email": "user@example.com",
                "operation_id": "123e4567-e89b-12d3-a456-426614174001",
                "operation_type": "INVEST_EXCLUSIVE",
                "movement": {"from_bucket": "AVAILABLE", "to_bucket": "LOCKED"},
            }
        }



