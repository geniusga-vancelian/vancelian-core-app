"""
Current user (me) API endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.core.users.models import User
from app.schemas.auth import MeResponse
from fastapi import HTTPException
from app.auth.dependencies import require_user_role, get_user_id_from_principal
from app.auth.oidc import Principal

router = APIRouter()


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Get current user info",
    description="Get current authenticated user information. Requires USER role.",
)
async def get_me(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> MeResponse:
    """
    Get current authenticated user information.
    
    Returns:
    - user_id: User UUID
    - email: User email address
    - first_name: User first name (if set)
    - last_name: User last name (if set)
    - status: User status (ACTIVE, SUSPENDED)
    
    Requires authentication (Bearer token) with USER role.
    """
    user_id = get_user_id_from_principal(principal)
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return MeResponse(
        user_id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        status=user.status.value,
    )

