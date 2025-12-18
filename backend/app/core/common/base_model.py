"""
Base model with common fields
"""

from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.infrastructure.database import Base


class BaseModel(Base):
    """
    Base model with common fields
    
    All models inherit from this base class and get:
    - id: UUID primary key
    - created_at: Timezone-aware timestamp
    - updated_at: Timezone-aware timestamp (nullable)
    
    Note: Some models (Account, LedgerEntry) override updated_at to be None.
    """
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

