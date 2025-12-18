"""
FastAPI dependencies for OIDC authentication and RBAC
"""

import logging
from functools import partial
from typing import List, Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from starlette.requests import Request as StarletteRequest

from app.infrastructure.database import get_db
from app.infrastructure.settings import get_settings
from app.core.security.models import Role
from app.auth.oidc import Principal, verify_jwt_token, get_verifier
from app.auth.principal import get_or_create_user_from_principal
from app.utils.trace_id import get_trace_id, trace_id_context

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def extract_bearer_token(
    authorization: Optional[str] = Header(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """
    Extract Bearer token from Authorization header.
    
    Supports both:
    - HTTPBearer dependency (standard)
    - Manual header parsing (fallback)
    """
    if credentials:
        return credentials.credentials
    
    if authorization:
        # Parse "Bearer <token>" manually
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
    
    return None


async def require_auth(
    request: StarletteRequest,
    token: Optional[str] = Depends(extract_bearer_token),
    db: Session = Depends(get_db),
) -> Principal:
    """
    FastAPI dependency to require authentication.
    
    Verifies JWT token and returns Principal.
    Automatically provisions User record on first authentication.
    
    Raises:
        HTTPException 401: If token is missing or invalid
    """
    if not token:
        settings = get_settings()
        trace_id = get_trace_id(request) or trace_id_context.get()
        if not settings.OIDC_ISSUER_URL:
            # OIDC not configured, skip auth in development
            logger.warning("OIDC not configured, skipping authentication (development mode)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": {
                        "code": "AUTH_REQUIRED",
                        "message": "Authentication required but OIDC not configured",
                        "trace_id": trace_id,
                    }
                },
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_REQUIRED",
                    "message": "Missing or invalid Authorization header",
                    "trace_id": trace_id,
                }
            },
        )
    
    try:
        # Verify token
        principal = verify_jwt_token(token)
        
        # Provision user (create if not exists)
        user = get_or_create_user_from_principal(db, principal)
        
        # Attach user_id to principal for convenience
        principal.user_id = user.id
        
        return principal
    
    except Exception as e:
        logger.warning(f"Authentication failed: {e}")
        
        error_code = "AUTH_INVALID_TOKEN"
        error_message = "Invalid or expired token"
        
        if "expired" in str(e).lower():
            error_code = "AUTH_TOKEN_EXPIRED"
            error_message = "Token has expired"
        elif "signature" in str(e).lower():
            error_code = "AUTH_INVALID_SIGNATURE"
            error_message = "Invalid token signature"
        
        trace_id = get_trace_id(request) or trace_id_context.get()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": error_code,
                    "message": error_message,
                    "trace_id": trace_id,
                }
            },
        )


def _map_role_to_internal(role_str: str) -> Optional[Role]:
    """Map external role string to internal Role enum"""
    role_upper = role_str.upper()
    
    # Direct mapping
    if role_upper == "USER":
        return Role.USER
    elif role_upper == "ADMIN":
        return Role.ADMIN
    elif role_upper == "COMPLIANCE":
        return Role.COMPLIANCE
    elif role_upper == "OPS":
        return Role.OPS
    elif role_upper == "READ_ONLY" or role_upper == "READONLY":
        return Role.READ_ONLY
    
    # Fallback: check if it matches any Role value
    try:
        return Role(role_upper)
    except ValueError:
        return None


def _principal_has_role(principal: Principal, required_role: Role) -> bool:
    """Check if principal has the required role"""
    if not principal.roles:
        # Default to USER for /api/v1/* if no roles
        return required_role == Role.USER
    
    for role_str in principal.roles:
        mapped_role = _map_role_to_internal(role_str)
        if mapped_role == required_role:
            return True
    
    return False


async def _require_roles_impl(
    allowed_roles: tuple[Role, ...],
    request: StarletteRequest,
    principal: Principal = Depends(require_auth),
) -> Principal:
    """
    Internal implementation for role checking.
    """
    if not allowed_roles:
        # No role requirement, just require auth
        return principal
    
    # Check if principal has at least one of the required roles
    has_role = any(_principal_has_role(principal, role) for role in allowed_roles)
    
    if not has_role:
        logger.warning(
            f"Access denied: principal {principal.subject} with roles {principal.roles} "
            f"does not have required roles {[r.value for r in allowed_roles]}"
        )
        
        trace_id = get_trace_id(request) or trace_id_context.get()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": f"Access denied: required roles {[r.value for r in allowed_roles]}",
                    "trace_id": trace_id,
                }
            },
        )
    
    return principal


def require_roles(*allowed_roles: Role):
    """
    Factory function to create a FastAPI dependency that requires specific roles.
    
    Usage:
        @router.get("/admin/users")
        async def list_users(
            principal: Principal = Depends(require_roles(Role.ADMIN, Role.OPS))
        ):
            ...
    
    Raises:
        HTTPException 403: If user doesn't have required role
    """
    return partial(_require_roles_impl, allowed_roles)


# Convenience dependencies for common role requirements
def require_user_role():
    """Require USER role (for /api/v1/* endpoints)"""
    return require_roles(Role.USER)


def require_admin_role():
    """Require one of: ADMIN, COMPLIANCE, OPS, READ_ONLY (for /admin/v1/* endpoints)"""
    return require_roles(Role.ADMIN, Role.COMPLIANCE, Role.OPS, Role.READ_ONLY)


def require_compliance_or_ops():
    """Require COMPLIANCE or OPS role"""
    return require_roles(Role.COMPLIANCE, Role.OPS)


# Helper to get user_id from principal
def get_user_id_from_principal(principal: Principal) -> UUID:
    """
    Extract user_id from principal (must have user_id attribute set by require_auth)
    
    Note: Principal.user_id is set dynamically by require_auth after user provisioning.
    """
    if not hasattr(principal, 'user_id'):
        raise ValueError("Principal missing user_id - ensure require_auth was called")
    return principal.user_id

