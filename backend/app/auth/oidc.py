"""
OIDC authentication and Principal model
"""

from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel


class Principal(BaseModel):
    """
    Principal represents the authenticated user/entity.
    
    This is populated from OIDC/JWT token claims.
    """
    sub: str  # Subject (user identifier from OIDC provider)
    email: Optional[str] = None
    roles: list[str] = []  # User roles extracted from token
    claims: Dict[str, Any] = {}  # Additional claims from token
    
    def get_user_id(self) -> Optional[UUID]:
        """
        Extract user_id from principal.
        
        TODO: Implement real extraction logic based on your OIDC provider.
        This might extract from sub, or from a custom claim.
        """
        # TODO: Implement based on your OIDC provider's token structure
        # For now, return None to indicate not implemented
        return None
