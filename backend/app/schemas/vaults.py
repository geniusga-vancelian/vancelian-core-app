"""
Vault API request/response schemas
"""

from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from typing import Optional, List
from datetime import datetime


class VaultSnapshot(BaseModel):
    """Vault snapshot for responses"""
    code: str = Field(..., description="Vault code (e.g., FLEX, AVENIR)")
    name: str = Field(..., description="Vault display name")
    status: str = Field(..., description="Vault status (ACTIVE, PAUSED, CLOSED)")
    cash_balance: str = Field(..., description="Vault cash balance (from ledger)")
    total_aum: str = Field(..., description="Total AUM (sum of vault_accounts.principal)")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "FLEX",
                "name": "FLEX - Flexible Vault",
                "status": "ACTIVE",
                "cash_balance": "50000.00",
                "total_aum": "45000.00",
            }
        }


class VaultAccountMeResponse(BaseModel):
    """User's vault account response"""
    vault_account_id: str = Field(..., description="VaultAccount UUID")
    principal: str = Field(..., description="Total deposits (principal)")
    available_balance: str = Field(..., description="Available balance for withdrawal")
    locked_until: Optional[str] = Field(None, description="ISO 8601 timestamp if locked (e.g., AVENIR)")
    vault: VaultSnapshot = Field(..., description="Vault snapshot")

    class Config:
        json_schema_extra = {
            "example": {
                "vault_account_id": "123e4567-e89b-12d3-a456-426614174000",
                "principal": "10000.00",
                "available_balance": "10000.00",
                "locked_until": None,
                "vault": {
                    "code": "FLEX",
                    "name": "FLEX - Flexible Vault",
                    "status": "ACTIVE",
                    "cash_balance": "50000.00",
                    "total_aum": "45000.00",
                }
            }
        }


class DepositRequest(BaseModel):
    """Request schema for vault deposit"""
    amount: Decimal = Field(..., gt=0, description="Deposit amount (must be > 0)")
    currency: str = Field(default="AED", description="Currency code (default: AED)")

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Quantize amount to 2 decimal places"""
        return v.quantize(Decimal('0.01'))

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Normalize currency to uppercase"""
        return v.upper()

    class Config:
        json_schema_extra = {
            "example": {
                "amount": "1000.00",
                "currency": "AED",
            }
        }


class DepositResponse(BaseModel):
    """Response schema for vault deposit"""
    operation_id: str = Field(..., description="Operation UUID")
    vault_account_id: str = Field(..., description="VaultAccount UUID")
    vault: VaultSnapshot = Field(..., description="Vault snapshot after deposit")

    class Config:
        json_schema_extra = {
            "example": {
                "operation_id": "123e4567-e89b-12d3-a456-426614174000",
                "vault_account_id": "123e4567-e89b-12d3-a456-426614174001",
                "vault": {
                    "code": "FLEX",
                    "name": "FLEX - Flexible Vault",
                    "status": "ACTIVE",
                    "cash_balance": "51000.00",
                    "total_aum": "46000.00",
                }
            }
        }


class WithdrawRequest(BaseModel):
    """Request schema for vault withdrawal"""
    amount: Decimal = Field(..., gt=0, description="Withdrawal amount (must be > 0)")
    currency: str = Field(default="AED", description="Currency code (default: AED)")
    reason: Optional[str] = Field(None, description="Optional reason/note")

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Quantize amount to 2 decimal places"""
        return v.quantize(Decimal('0.01'))

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Normalize currency to uppercase"""
        return v.upper()

    class Config:
        json_schema_extra = {
            "example": {
                "amount": "500.00",
                "currency": "AED",
                "reason": "Need funds for investment",
            }
        }


class WithdrawResponse(BaseModel):
    """Response schema for vault withdrawal"""
    request_id: str = Field(..., description="WithdrawalRequest UUID")
    status: str = Field(..., description="Status: EXECUTED or PENDING")
    operation_id: Optional[str] = Field(None, description="Operation UUID (only if EXECUTED)")
    vault: VaultSnapshot = Field(..., description="Vault snapshot after withdrawal")

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "EXECUTED",
                "operation_id": "123e4567-e89b-12d3-a456-426614174001",
                "vault": {
                    "code": "FLEX",
                    "name": "FLEX - Flexible Vault",
                    "status": "ACTIVE",
                    "cash_balance": "50500.00",
                    "total_aum": "45500.00",
                }
            }
        }


class WithdrawalListItem(BaseModel):
    """Withdrawal request list item"""
    request_id: str = Field(..., description="WithdrawalRequest UUID")
    amount: str = Field(..., description="Withdrawal amount")
    currency: str = Field(..., description="Currency code")
    status: str = Field(..., description="Status (PENDING, EXECUTED, CANCELLED)")
    reason: Optional[str] = Field(None, description="Reason/note")
    created_at: str = Field(..., description="ISO 8601 timestamp")
    executed_at: Optional[str] = Field(None, description="ISO 8601 timestamp (if EXECUTED)")

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "123e4567-e89b-12d3-a456-426614174000",
                "amount": "500.00",
                "currency": "AED",
                "status": "PENDING",
                "reason": "Need funds",
                "created_at": "2025-12-25T12:00:00Z",
                "executed_at": None,
            }
        }


class WithdrawalListResponse(BaseModel):
    """Response schema for withdrawal list"""
    withdrawals: List[WithdrawalListItem] = Field(..., description="List of withdrawal requests")

    class Config:
        json_schema_extra = {
            "example": {
                "withdrawals": [
                    {
                        "request_id": "123e4567-e89b-12d3-a456-426614174000",
                        "amount": "500.00",
                        "currency": "AED",
                        "status": "PENDING",
                        "reason": "Need funds",
                        "created_at": "2025-12-25T12:00:00Z",
                        "executed_at": None,
                    }
                ]
            }
        }


# Admin schemas

class AdminVaultRow(BaseModel):
    """Admin vault list row"""
    id: str = Field(..., description="Vault UUID")
    code: str = Field(..., description="Vault code")
    name: str = Field(..., description="Vault name")
    status: str = Field(..., description="Vault status")
    cash_balance: str = Field(..., description="Vault cash balance")
    total_aum: str = Field(..., description="Total AUM")
    pending_withdrawals_count: int = Field(..., description="Count of pending withdrawals")
    pending_withdrawals_amount: str = Field(..., description="Sum of pending withdrawal amounts")
    updated_at: Optional[str] = Field(None, description="ISO 8601 timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "code": "FLEX",
                "name": "FLEX - Flexible Vault",
                "status": "ACTIVE",
                "cash_balance": "50000.00",
                "total_aum": "45000.00",
                "pending_withdrawals_count": 2,
                "pending_withdrawals_amount": "1000.00",
                "updated_at": "2025-12-25T12:00:00Z",
            }
        }


class AdminVaultsListResponse(BaseModel):
    """Response schema for admin vaults list"""
    vaults: List[AdminVaultRow] = Field(..., description="List of vaults")


class SystemWalletInfo(BaseModel):
    """System wallet balance info"""
    available: str = Field(..., description="Available balance")
    locked: str = Field(..., description="Locked balance")
    blocked: str = Field(..., description="Blocked balance")


class AdminPortfolioResponse(BaseModel):
    """Response schema for admin vault portfolio"""
    vault: VaultSnapshot = Field(..., description="Vault snapshot")
    accounts_count: int = Field(..., description="Number of user accounts in vault")
    system_wallet: SystemWalletInfo = Field(..., description="System wallet balances")
    pending_withdrawals_count: int = Field(..., description="Count of pending withdrawals")


class ProcessWithdrawalsResponse(BaseModel):
    """Response schema for process withdrawals"""
    processed_count: int = Field(..., description="Number of withdrawals processed")
    remaining_count: int = Field(..., description="Number of remaining pending withdrawals")

    class Config:
        json_schema_extra = {
            "example": {
                "processed_count": 3,
                "remaining_count": 2,
            }
        }


class VestingReleaseSummaryResponse(BaseModel):
    """Response schema for vesting release summary"""
    matured_found: int = Field(..., description="Number of mature lots found")
    executed_count: int = Field(..., description="Number of lots successfully released")
    executed_amount: str = Field(..., description="Total amount released")
    skipped_count: int = Field(..., description="Number of lots skipped")
    errors_count: int = Field(..., description="Number of errors encountered")
    errors: List[str] = Field(default_factory=list, description="List of error messages")
    locks_closed_count: int = Field(..., description="Number of wallet_locks closed")
    locks_missing_count: int = Field(..., description="Number of lots with missing wallet_locks")
    trace_id: str = Field(..., description="Trace ID used for this run")
    as_of_date: str = Field(..., description="Date used for maturity check (ISO format)")


class VestingTimelineItem(BaseModel):
    """Vesting timeline item"""
    date: str = Field(..., description="Release date (YYYY-MM-DD)")
    amount: str = Field(..., description="Amount to be released on this date")


class VestingTimelineResponse(BaseModel):
    """Response schema for vesting timeline"""
    vault_code: str = Field(..., description="Vault code (e.g., AVENIR)")
    currency: str = Field(..., description="Currency code")
    items: List[VestingTimelineItem] = Field(..., description="List of release dates and amounts")
