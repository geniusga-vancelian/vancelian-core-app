"""
Principal management and user provisioning
"""

import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.users.models import User, UserStatus
from app.auth.oidc import Principal

logger = logging.getLogger(__name__)


def get_or_create_user_from_principal(
    db: Session,
    principal: Principal,
) -> User:
    """
    Get or create User record from OIDC Principal.
    
    On first authentication:
    - Creates User record with email (or sub if no email)
    - Sets status to ACTIVE by default
    - Stores external_subject (OIDC sub) in metadata or dedicated column
    
    Returns existing or newly created User.
    """
    # Try to find user by email first
    user: Optional[User] = None
    
    if principal.email:
        user = db.execute(
            select(User).where(User.email == principal.email)
        ).scalar_one_or_none()
    
    # If not found by email, try by external_subject (if column exists)
    if not user:
        # Check if external_subject column exists (dynamic check)
        try:
            if hasattr(User, 'external_subject'):
                user = db.execute(
                    select(User).where(User.external_subject == principal.subject)
                ).scalar_one_or_none()
        except Exception as e:
            logger.debug(f"external_subject column not available: {e}")
    
    # Create user if not found
    if not user:
        # Use email if available, otherwise use sub as email
        email = principal.email or f"{principal.subject}@oidc.local"
        
        # Ensure email uniqueness
        existing_by_email = db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
        
        if existing_by_email:
            user = existing_by_email
        else:
            user = User(
                email=email,
                status=UserStatus.ACTIVE,
                external_subject=principal.subject,  # Store OIDC subject
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            logger.info(f"Created new user from OIDC principal: {user.id}, email: {email}, sub: {principal.subject}")
    
    # Update external_subject if not set
    if hasattr(User, 'external_subject') and not user.external_subject:
        user.external_subject = principal.subject
        db.commit()
        db.refresh(user)
    
    return user

