"""
RBAC dependencies for FastAPI
"""

from typing import List
from fastapi import HTTPException, status
from app.core.security.models import Role


async def require_role(allowed_roles: List[Role]):
    """
    FastAPI dependency to require specific roles
    This is a stub - real implementation will check JWT token and user roles
    """
    # TODO: Implement OIDC/JWT token validation
    # TODO: Extract user role from token
    # TODO: Check if user role is in allowed_roles
    # For now, this is a placeholder that always raises 401

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required - RBAC stub not implemented yet",
    )


async def require_user_role():
    """Require USER role"""
    return await require_role([Role.USER])


async def require_admin_role():
    """Require ADMIN role"""
    return await require_role([Role.ADMIN])


async def require_compliance_role():
    """Require COMPLIANCE role"""
    return await require_role([Role.COMPLIANCE])


async def require_ops_role():
    """Require OPS role"""
    return await require_role([Role.OPS])



