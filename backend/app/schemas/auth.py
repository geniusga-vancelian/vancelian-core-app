"""
Authentication API schemas
"""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    first_name: str = Field(None, description="User first name")
    last_name: str = Field(None, description="User last name")


class RegisterResponse(BaseModel):
    """User registration response"""
    user_id: str = Field(..., description="Created user UUID")
    email: str = Field(..., description="User email address")
    message: str = Field(default="User registered successfully")


class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class LoginResponse(BaseModel):
    """User login response"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user_id: str = Field(..., description="User UUID")
    email: str = Field(..., description="User email address")


class MeResponse(BaseModel):
    """Current user info response"""
    user_id: str = Field(..., description="User UUID")
    email: str = Field(..., description="User email address")
    first_name: str = Field(None, description="User first name")
    last_name: str = Field(None, description="User last name")
    status: str = Field(..., description="User status (ACTIVE, SUSPENDED)")

