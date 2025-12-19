"""
Offer models - Exclusive investment offers
"""

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, Numeric, Text, DateTime, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum
from app.core.common.base_model import BaseModel


class OfferStatus(str, enum.Enum):
    """Offer status enum"""
    DRAFT = "DRAFT"
    LIVE = "LIVE"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"


class OfferInvestmentStatus(str, enum.Enum):
    """Offer investment status enum"""
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class Offer(BaseModel):
    """
    Offer model - Represents an exclusive investment offer
    
    Features:
    - max_amount: Maximum amount that can be committed
    - committed_amount: Current amount committed (sum of accepted investments)
    - status: DRAFT, LIVE, PAUSED, CLOSED
    - Enforces max_amount limit via row-level locking
    """
    
    __tablename__ = "offers"
    
    code = Column(String(50), unique=True, nullable=False, index=True)  # Short human slug like "NEST-ALBARARI-001"
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    currency = Column(String(3), nullable=False, default="AED", index=True)  # ISO 4217
    max_amount = Column(Numeric(24, 8), nullable=False)  # Maximum amount that can be committed
    committed_amount = Column(Numeric(24, 8), nullable=False, default=0)  # Current amount committed
    maturity_date = Column(DateTime(timezone=True), nullable=True)  # Maturity date (timestamptz)
    status = Column(SQLEnum(OfferStatus, name="offer_status", create_constraint=True), nullable=False, default=OfferStatus.DRAFT, index=True)
    offer_metadata = Column('metadata', JSONB, nullable=True)  # Flexible JSONB metadata (DB column: metadata)
    
    # Relationships
    investments = relationship("OfferInvestment", back_populates="offer", lazy="select")
    
    # Table-level constraints
    __table_args__ = (
        CheckConstraint('max_amount > 0', name='check_max_amount_positive'),
        CheckConstraint('committed_amount >= 0', name='check_committed_amount_non_negative'),
        CheckConstraint('committed_amount <= max_amount', name='check_committed_not_exceed_max'),
        Index('idx_offer_status_currency', 'status', 'currency'),
    )


class OfferInvestment(BaseModel):
    """
    OfferInvestment model - Represents a user's investment in an offer
    
    Features:
    - requested_amount: Amount user wants to invest
    - accepted_amount: Amount actually accepted (may be less if offer is near max_amount)
    - status: PENDING, ACCEPTED, REJECTED
    - idempotency_key: Prevents double-click duplication
    - operation_id: Links to ledger operation that moved funds
    """
    
    __tablename__ = "offer_investments"
    
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id", name="fk_offer_investments_offer_id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", name="fk_offer_investments_user_id"), nullable=False, index=True)
    requested_amount = Column(Numeric(24, 8), nullable=False)
    accepted_amount = Column(Numeric(24, 8), nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="AED")
    status = Column(SQLEnum(OfferInvestmentStatus, name="offer_investment_status", create_constraint=True), nullable=False, default=OfferInvestmentStatus.PENDING, index=True)
    idempotency_key = Column(String(255), nullable=True, unique=True, index=True)  # Prevents double-click duplication
    operation_id = Column(UUID(as_uuid=True), ForeignKey("operations.id", name="fk_offer_investments_operation_id"), nullable=True, index=True)  # Link to ledger operation
    
    # Relationships
    offer = relationship("Offer", back_populates="investments")
    user = relationship("User", foreign_keys=[user_id])
    operation = relationship("Operation", foreign_keys=[operation_id])
    
    # Table-level constraints
    __table_args__ = (
        CheckConstraint('requested_amount > 0', name='check_requested_amount_positive'),
        CheckConstraint('accepted_amount >= 0', name='check_accepted_amount_non_negative'),
        CheckConstraint('accepted_amount <= requested_amount', name='check_accepted_not_exceed_requested'),
        Index('idx_offer_investments_offer_user', 'offer_id', 'user_id'),
        Index('idx_offer_investments_offer_status', 'offer_id', 'status'),
        Index('idx_offer_investments_user_status', 'user_id', 'status'),
    )

