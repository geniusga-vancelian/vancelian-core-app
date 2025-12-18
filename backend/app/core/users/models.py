"""
User model
"""

from sqlalchemy import Column, String, Enum as SQLEnum
import enum
from app.core.common.base_model import BaseModel


class UserStatus(str, enum.Enum):
    """User status enum"""
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class User(BaseModel):
    """User model"""

    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(SQLEnum(UserStatus, name="user_status"), nullable=False, default=UserStatus.ACTIVE)
    
    # OIDC subject (external identifier from identity provider)
    # Note: Uniqueness is enforced via partial unique index (WHERE external_subject IS NOT NULL)
    # This allows multiple NULL values while ensuring non-NULL values are unique
    external_subject = Column(String(255), nullable=True, index=True)

