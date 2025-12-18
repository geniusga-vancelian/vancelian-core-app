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
    transaction_id: str = Field(..., description="Transaction UUID")
    type: str = Field(..., description="Transaction type (DEPOSIT, WITHDRAWAL, INVESTMENT)")
    status: str = Field(..., description="Transaction status (INITIATED, COMPLIANCE_REVIEW, AVAILABLE, FAILED, CANCELLED)")
    amount: str = Field(..., description="Transaction amount (sum of ledger entries affecting user wallet)")
    currency: str = Field(..., description="ISO 4217 currency code (e.g., AED)")
    created_at: str = Field(..., description="ISO 8601 timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
                "type": "DEPOSIT",
                "status": "AVAILABLE",
                "amount": "10000.00",
                "currency": "AED",
                "created_at": "2025-12-18T00:00:00Z",
            }
        }


