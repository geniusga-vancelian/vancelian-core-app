"""
Offer models - Exclusive investment offers
"""

from decimal import Decimal
from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, Numeric, Text, DateTime, Index, CheckConstraint, Integer, BigInteger, Boolean
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


class InvestmentIntentStatus(str, enum.Enum):
    """InvestmentIntent status enum (v1.1)"""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class Offer(BaseModel):
    """
    Offer model - Represents an exclusive investment offer (v1.1)
    
    Features:
    - max_amount: Maximum amount that can be invested (hard cap)
    - invested_amount: Current amount invested (sum of confirmed investments)
    - remaining_amount: Computed as max_amount - invested_amount (MUST NEVER go below 0)
    - committed_amount: Legacy field (alias for invested_amount, kept for backward compatibility)
    - status: DRAFT, LIVE, PAUSED, CLOSED
    - Enforces max_amount limit via row-level locking (SELECT ... FOR UPDATE)
    """
    
    __tablename__ = "offers"
    
    code = Column(String(50), unique=True, nullable=False, index=True)  # Short human slug like "NEST-ALBARARI-001"
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    currency = Column(String(3), nullable=False, default="AED", index=True)  # ISO 4217
    max_amount = Column(Numeric(24, 8), nullable=False)  # Maximum amount that can be invested
    invested_amount = Column(Numeric(24, 8), nullable=False, default=0)  # Current amount invested (v1.1)
    committed_amount = Column(Numeric(24, 8), nullable=False, default=0)  # Legacy: alias for invested_amount
    maturity_date = Column(DateTime(timezone=True), nullable=True)  # Maturity date (timestamptz)
    status = Column(SQLEnum(OfferStatus, name="offer_status", create_constraint=True), nullable=False, default=OfferStatus.DRAFT, index=True)
    offer_metadata = Column('metadata', JSONB, nullable=True)  # Flexible JSONB metadata (DB column: metadata)
    
    # Relationships
    investments = relationship("OfferInvestment", back_populates="offer", lazy="select")
    investment_intents = relationship("InvestmentIntent", back_populates="offer", lazy="select")
    media = relationship("OfferMedia", back_populates="offer", cascade="all, delete-orphan", lazy="select")
    documents = relationship("OfferDocument", back_populates="offer", cascade="all, delete-orphan", lazy="select")
    
    # Table-level constraints
    __table_args__ = (
        CheckConstraint('max_amount > 0', name='check_max_amount_positive'),
        CheckConstraint('invested_amount >= 0', name='check_invested_amount_non_negative'),
        CheckConstraint('invested_amount <= max_amount', name='check_invested_not_exceed_max'),
        CheckConstraint('committed_amount >= 0', name='check_committed_amount_non_negative'),
        CheckConstraint('committed_amount <= max_amount', name='check_committed_not_exceed_max'),
        Index('idx_offer_status_currency', 'status', 'currency'),
    )
    
    @property
    def remaining_amount(self) -> Decimal:
        """Compute remaining amount (MUST NEVER go below 0)"""
        remaining = self.max_amount - self.invested_amount
        return max(remaining, Decimal('0'))


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


class InvestmentIntent(BaseModel):
    """
    InvestmentIntent model (v1.1) - Represents a user's investment intent in an offer
    
    Lifecycle:
    - PENDING: Intent created, waiting for allocation
    - CONFIRMED: Allocation successful, funds moved to LOCKED
    - REJECTED: Allocation failed (offer full, insufficient funds, etc.)
    
    Features:
    - requested_amount: Amount user wants to invest
    - allocated_amount: Amount actually allocated (may be less if offer is near max_amount)
    - status: PENDING, CONFIRMED, REJECTED
    - idempotency_key: Prevents double-click duplication
    - operation_id: Links to ledger operation that moved funds (only if CONFIRMED)
    """
    
    __tablename__ = "investment_intents"
    
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id", name="fk_investment_intents_offer_id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", name="fk_investment_intents_user_id"), nullable=False, index=True)
    requested_amount = Column(Numeric(24, 8), nullable=False)
    allocated_amount = Column(Numeric(24, 8), nullable=False, default=0)  # Amount actually allocated
    currency = Column(String(3), nullable=False, default="AED")
    status = Column(SQLEnum(InvestmentIntentStatus, name="investment_intent_status", create_constraint=True), nullable=False, default=InvestmentIntentStatus.PENDING, index=True)
    idempotency_key = Column(String(255), nullable=True, unique=True, index=True)  # Prevents double-click duplication
    operation_id = Column(UUID(as_uuid=True), ForeignKey("operations.id", name="fk_investment_intents_operation_id"), nullable=True, index=True)  # Link to ledger operation (only if CONFIRMED)
    
    # Relationships
    offer = relationship("Offer", back_populates="investment_intents")
    user = relationship("User", foreign_keys=[user_id])
    operation = relationship("Operation", foreign_keys=[operation_id])
    
    # Table-level constraints
    __table_args__ = (
        CheckConstraint('requested_amount > 0', name='check_intent_requested_amount_positive'),
        CheckConstraint('allocated_amount >= 0', name='check_intent_allocated_amount_non_negative'),
        CheckConstraint('allocated_amount <= requested_amount', name='check_intent_allocated_not_exceed_requested'),
        Index('idx_investment_intents_offer_user', 'offer_id', 'user_id'),
        Index('idx_investment_intents_offer_status', 'offer_id', 'status'),
        Index('idx_investment_intents_user_status', 'user_id', 'status'),
    )


class MediaType(str, enum.Enum):
    """Media type enum"""
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


class MediaVisibility(str, enum.Enum):
    """Media visibility enum"""
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class OfferMedia(BaseModel):
    """
    OfferMedia model - Represents media files (images/videos) for an offer stored in S3/R2
    
    Features:
    - Stores metadata only (actual file in S3/R2)
    - Supports presigned URLs for upload/download
    - Supports sorting and cover image selection
    """
    
    __tablename__ = "offer_media"
    
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id", name="fk_offer_media_offer_id"), nullable=False, index=True)
    type = Column(SQLEnum(MediaType, name="media_type", create_constraint=True), nullable=False, index=True)
    key = Column(String(512), unique=True, nullable=False, index=True)  # S3/R2 object key
    url = Column(String(1024), nullable=True)  # Optional public CDN URL
    mime_type = Column(String(100), nullable=False)  # e.g., image/jpeg, video/mp4
    size_bytes = Column(BigInteger, nullable=False)
    width = Column(Integer, nullable=True)  # For images/videos
    height = Column(Integer, nullable=True)  # For images/videos
    duration_seconds = Column(Integer, nullable=True)  # For videos
    sort_order = Column(Integer, nullable=False, default=0, index=True)
    is_cover = Column(Boolean, nullable=False, default=False, index=True)
    visibility = Column(SQLEnum(MediaVisibility, name="media_visibility", create_constraint=True), nullable=False, default=MediaVisibility.PUBLIC, index=True)
    
    # Relationships
    offer = relationship("Offer", back_populates="media")
    
    # Table-level constraints
    __table_args__ = (
        CheckConstraint('size_bytes > 0', name='check_media_size_positive'),
        CheckConstraint('sort_order >= 0', name='check_media_sort_order_non_negative'),
        Index('idx_offer_media_offer_sort', 'offer_id', 'sort_order'),
    )


class DocumentKind(str, enum.Enum):
    """Document kind enum"""
    BROCHURE = "BROCHURE"
    MEMO = "MEMO"
    PROJECTIONS = "PROJECTIONS"
    VALUATION = "VALUATION"
    OTHER = "OTHER"


class DocumentVisibility(str, enum.Enum):
    """Document visibility enum"""
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class OfferDocument(BaseModel):
    """
    OfferDocument model - Represents documents (PDFs, etc.) for an offer stored in S3/R2
    
    Features:
    - Stores metadata only (actual file in S3/R2)
    - Supports presigned URLs for upload/download
    """
    
    __tablename__ = "offer_documents"
    
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id", name="fk_offer_documents_offer_id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    kind = Column(SQLEnum(DocumentKind, name="document_kind", create_constraint=True), nullable=False, index=True)
    key = Column(String(512), unique=True, nullable=False, index=True)  # S3/R2 object key
    mime_type = Column(String(100), nullable=False)  # e.g., application/pdf
    size_bytes = Column(BigInteger, nullable=False)
    visibility = Column(SQLEnum(DocumentVisibility, name="document_visibility", create_constraint=True), nullable=False, default=DocumentVisibility.PUBLIC, index=True)
    url = Column(String(1024), nullable=True)  # Optional public CDN URL
    
    # Relationships
    offer = relationship("Offer", back_populates="documents")
    
    # Table-level constraints
    __table_args__ = (
        CheckConstraint('size_bytes > 0', name='check_document_size_positive'),
    )
