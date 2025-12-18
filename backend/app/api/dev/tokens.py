"""
DEV-ONLY endpoints for JWT token generation
⚠️ These endpoints are ONLY available in development mode
"""

import jwt
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel

from app.infrastructure.settings import get_settings
from app.utils.trace_id import trace_id_context

router = APIRouter(prefix="/token", tags=["dev-tokens"])
settings = get_settings()


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int  # seconds
    subject: str
    email: str
    roles: list[str]


@router.post(
    "/admin",
    response_model=TokenResponse,
    summary="Generate admin token (DEV-ONLY)",
    description="""
    **DEV-ONLY**: Generate a JWT token with ADMIN and COMPLIANCE roles.
    
    This endpoint is ONLY available when DEV_MODE=true.
    ⚠️ Never expose this endpoint in production!
    
    The generated token:
    - Is signed with JWT_SECRET using HS256 algorithm
    - Contains roles: ADMIN, COMPLIANCE
    - Expires in 7 days by default
    - Uses a random UUID as subject unless provided
    """,
)
async def generate_admin_token(
    subject: Optional[str] = Query(
        default=None,
        description="Subject (sub) claim. If not provided, a random UUID will be generated"
    ),
    expires_in_days: int = Query(
        default=7,
        ge=1,
        le=30,
        description="Token expiration in days (1-30)"
    ),
) -> TokenResponse:
    """
    Generate a DEV-ONLY JWT token with ADMIN and COMPLIANCE roles.
    """
    # Security check: Only allow if DEV_MODE is enabled
    if not settings.DEV_MODE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,  # 404 to hide endpoint existence
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Endpoint not found",
                    "trace_id": trace_id_context.get(),
                }
            },
        )
    
    # Check JWT_SECRET is configured
    if not settings.JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "CONFIG_ERROR",
                    "message": "JWT_SECRET not configured. Cannot generate tokens.",
                    "trace_id": trace_id_context.get(),
                }
            },
        )
    
    # Generate subject if not provided
    if not subject:
        subject = str(uuid.uuid4())
    
    # Calculate expiration
    now = datetime.now(timezone.utc)
    exp = int((now + timedelta(days=expires_in_days)).timestamp())
    
    # Create payload
    payload = {
        "sub": subject,
        "email": "admin@vancelian.dev",
        "roles": ["ADMIN", "COMPLIANCE"],
        "exp": exp,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),  # Not before
    }
    
    # Generate token
    try:
        token = jwt.encode(
            payload,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "TOKEN_GENERATION_ERROR",
                    "message": f"Failed to generate token: {str(e)}",
                    "trace_id": trace_id_context.get(),
                }
            },
        )
    
    return TokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in=expires_in_days * 24 * 3600,  # Convert days to seconds
        subject=subject,
        email="admin@vancelian.dev",
        roles=["ADMIN", "COMPLIANCE"],
    )


@router.post(
    "/user",
    response_model=TokenResponse,
    summary="Generate user token (DEV-ONLY)",
    description="""
    **DEV-ONLY**: Generate a JWT token with USER role.
    
    This endpoint is ONLY available when DEV_MODE=true.
    ⚠️ Never expose this endpoint in production!
    
    The generated token:
    - Is signed with JWT_SECRET using HS256 algorithm
    - Contains role: USER
    - Expires in 7 days by default
    - Uses provided subject/email or defaults
    """,
)
async def generate_user_token(
    subject: Optional[str] = Query(
        default="11111111-1111-1111-1111-111111111111",
        description="Subject (sub) claim"
    ),
    email: Optional[str] = Query(
        default="user@vancelian.dev",
        description="Email claim"
    ),
    expires_in_days: int = Query(
        default=7,
        ge=1,
        le=30,
        description="Token expiration in days (1-30)"
    ),
) -> TokenResponse:
    """
    Generate a DEV-ONLY JWT token with USER role.
    """
    # Security check: Only allow if DEV_MODE is enabled
    if not settings.DEV_MODE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,  # 404 to hide endpoint existence
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Endpoint not found",
                    "trace_id": trace_id_context.get(),
                }
            },
        )
    
    # Check JWT_SECRET is configured
    if not settings.JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "CONFIG_ERROR",
                    "message": "JWT_SECRET not configured. Cannot generate tokens.",
                    "trace_id": trace_id_context.get(),
                }
            },
        )
    
    # Calculate expiration
    now = datetime.now(timezone.utc)
    exp = int((now + timedelta(days=expires_in_days)).timestamp())
    
    # Create payload
    payload = {
        "sub": subject,
        "email": email,
        "roles": ["USER"],
        "exp": exp,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),  # Not before
    }
    
    # Generate token
    try:
        token = jwt.encode(
            payload,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "TOKEN_GENERATION_ERROR",
                    "message": f"Failed to generate token: {str(e)}",
                    "trace_id": trace_id_context.get(),
                }
            },
        )
    
    return TokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in=expires_in_days * 24 * 3600,  # Convert days to seconds
        subject=subject,
        email=email,
        roles=["USER"],
    )

