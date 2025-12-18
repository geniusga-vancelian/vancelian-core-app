"""
AuditLog model - Transversal audit trail
"""

from sqlalchemy import Column, String, ForeignKey, JSON, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.common.base_model import BaseModel
from app.core.security.models import Role


class AuditLog(BaseModel):
    """
    AuditLog model - Audit trail for all critical actions
    """

    __tablename__ = "audit_logs"

    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", name="fk_audit_logs_actor_user_id"), nullable=True, index=True)
    actor_role = Column(SQLEnum(Role, name="actor_role", create_constraint=True), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    before = Column(JSON, nullable=True)  # JSONB in PostgreSQL - state before action
    after = Column(JSON, nullable=True)  # JSONB in PostgreSQL - state after action
    reason = Column(Text, nullable=True)  # Required for sensitive actions
    ip = Column(String(45), nullable=True)  # IPv6 max length

    # Relationships
    actor = relationship("User", foreign_keys=[actor_user_id])

