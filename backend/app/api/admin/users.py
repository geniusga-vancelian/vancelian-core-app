"""
Users admin endpoints
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.core.users.models import User
from app.schemas.compliance import UserListItem, UserDetailResponse, ResolveUserRequest, ResolveUserResponse
from app.auth.dependencies import require_admin_role

router = APIRouter()


@router.get(
    "/users",
    response_model=List[UserListItem],
    summary="List users",
    description="List all users. Requires ADMIN role.",
)
async def list_users(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    principal = Depends(require_admin_role()),
) -> List[UserListItem]:
    """List all users"""
    users = db.query(User).order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    
    return [
        UserListItem(
            user_id=str(user.id),
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            status=user.status.value,
            created_at=user.created_at.isoformat() + "Z",
        )
        for user in users
    ]


@router.post(
    "/users/resolve",
    response_model=ResolveUserResponse,
    summary="Resolve user",
    description="Resolve user by email, external_subject, or user_id. Requires ADMIN role.",
)
async def resolve_user(
    request: ResolveUserRequest,
    db: Session = Depends(get_db),
    principal = Depends(require_admin_role()),
) -> ResolveUserResponse:
    """Resolve user by identifier"""
    user = None
    
    if request.user_id:
        try:
            user_id = UUID(request.user_id)
            user = db.query(User).filter(User.id == user_id).first()
        except ValueError:
            pass
    elif request.email:
        user = db.query(User).filter(User.email == request.email).first()
    elif request.external_subject:
        user = db.query(User).filter(User.external_subject == request.external_subject).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return ResolveUserResponse(
        user_id=str(user.id),
        email=user.email,
        found=True,
    )


@router.get(
    "/users/{user_id}",
    response_model=UserDetailResponse,
    summary="Get user by ID",
    description="Get user details by UUID. Requires ADMIN role.",
)
async def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    principal = Depends(require_admin_role()),
) -> UserDetailResponse:
    """Get user details by UUID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserDetailResponse(
        user_id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        status=user.status.value,
        external_subject=user.external_subject,
        created_at=user.created_at.isoformat() + "Z",
    )
