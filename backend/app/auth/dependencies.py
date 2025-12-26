"""
Authentication dependencies for FastAPI
"""

from uuid import UUID
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
import jwt as pyjwt
from datetime import datetime

from app.auth.oidc import Principal
from app.security.rbac import require_role, Role
from app.infrastructure.settings import get_settings
from app.infrastructure.database import get_db
from app.core.users.models import User

settings = get_settings()


async def get_current_principal(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> Principal:
    """
    Extract Principal from JWT token in Authorization header.
    
    For DEV mode: Supports Bearer token with JWT.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTHORIZATION_MISSING",
                    "message": "Authorization header missing",
                    "trace_id": "auth-check",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Extract token from "Bearer <token>"
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Decode JWT token
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        
        # Extract user info
        user_id_str = payload.get("sub")
        email = payload.get("email", "")
        # Extract roles from JWT claims (if present)
        roles = payload.get("roles", ["USER"])
        
        # Get user from database to extract roles
        if user_id_str:
            try:
                user_id = UUID(user_id_str)
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    return Principal(
                        sub=user_id_str,
                        email=email or user.email,
                        roles=roles,  # Use roles from JWT
                        claims=payload,
                    )
            except (ValueError, TypeError):
                pass
        
        # Fallback: create Principal from token claims
        return Principal(
            sub=user_id_str or "",
            email=email,
            roles=roles,  # Use roles from JWT
            claims=payload,
        )
        
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "TOKEN_EXPIRED",
                    "message": "Token expired",
                    "trace_id": "auth-check",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    except pyjwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": f"Invalid token: {str(e)}",
                    "trace_id": "auth-check",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_user_role():
    """Require USER role - returns dependency"""
    async def _check_role(principal: Principal = Depends(get_current_principal)):
        # Check if user has USER role
        if "USER" not in principal.roles and Role.USER.value not in principal.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions - USER role required"
            )
        return principal
    return _check_role


def require_admin_role():
    """Require ADMIN role - returns dependency"""
    async def _check_role(principal: Principal = Depends(get_current_principal)):
        if "ADMIN" not in principal.roles and Role.ADMIN.value not in principal.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions - ADMIN role required"
            )
        return principal
    return _check_role


def require_compliance_role():
    """Require COMPLIANCE role - returns dependency"""
    async def _check_role(principal: Principal = Depends(get_current_principal)):
        if "COMPLIANCE" not in principal.roles and Role.COMPLIANCE.value not in principal.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions - COMPLIANCE role required"
            )
        return principal
    return _check_role


def get_user_id_from_principal(principal: Principal) -> UUID:
    """
    Extract user_id from Principal object.
    
    Extracts user_id from principal.sub (JWT subject claim).
    """
    if not principal.sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid principal - missing user identifier"
        )
    
    try:
        return UUID(principal.sub)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid principal - invalid user identifier format"
        )
