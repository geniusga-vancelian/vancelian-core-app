"""
Compliance API schemas
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DepositListItem(BaseModel):
    """Deposit list item response schema"""
    transaction_id: str = Field(..., description="Transaction UUID")
    user_id: str = Field(..., description="User UUID")
    email: str = Field(..., description="User email")
    amount: str = Field(..., description="Deposit amount")
    currency: str = Field(..., description="ISO 4217 currency code")
    status: str = Field(..., description="Transaction status")
    created_at: str = Field(..., description="ISO 8601 timestamp")
    compliance_status: Optional[str] = Field(None, description="Compliance review status")


class UserListItem(BaseModel):
    """User list item response schema"""
    user_id: str = Field(..., description="User UUID")
    email: str = Field(..., description="User email")
    first_name: Optional[str] = Field(None, description="User first name")
    last_name: Optional[str] = Field(None, description="User last name")
    status: str = Field(..., description="User status (ACTIVE, SUSPENDED)")
    created_at: str = Field(..., description="ISO 8601 timestamp")


class UserDetailResponse(BaseModel):
    """User detail response schema"""
    user_id: str = Field(..., description="User UUID")
    email: str = Field(..., description="User email")
    first_name: Optional[str] = Field(None, description="User first name")
    last_name: Optional[str] = Field(None, description="User last name")
    phone: Optional[str] = Field(None, description="User phone")
    status: str = Field(..., description="User status (ACTIVE, SUSPENDED)")
    external_subject: Optional[str] = Field(None, description="OIDC external subject")
    created_at: str = Field(..., description="ISO 8601 timestamp")


class ResolveUserRequest(BaseModel):
    """Resolve user request schema"""
    email: Optional[str] = Field(None, description="User email")
    external_subject: Optional[str] = Field(None, description="OIDC external subject")
    user_id: Optional[str] = Field(None, description="User UUID")


class ResolveUserResponse(BaseModel):
    """Resolve user response schema"""
    user_id: str = Field(..., description="User UUID")
    email: str = Field(..., description="User email")
    found: bool = Field(..., description="Whether user was found")
