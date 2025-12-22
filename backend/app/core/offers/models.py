"""
Offer models - Exclusive investment offers
"""

from decimal import Decimal
from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, Numeric, Text, DateTime, Index, CheckConstraint, Integer, BigInteger, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.orm import remote
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
    
    # Marketing V1.1 fields
    cover_media_id = Column(UUID(as_uuid=True), ForeignKey("offer_media.id", name="fk_offers_cover_media_id"), nullable=True, index=True)  # Cover image media ID
    promo_video_media_id = Column(UUID(as_uuid=True), ForeignKey("offer_media.id", name="fk_offers_promo_video_media_id"), nullable=True, index=True)  # Promo video media ID
    location_label = Column(String(255), nullable=True)  # Location label (e.g., "Unit 2308, Binghatti Onyx, JVC, Dubai, UAE")
    location_lat = Column(Numeric(10, 7), nullable=True)  # Latitude (decimal degrees)
    location_lng = Column(Numeric(10, 7), nullable=True)  # Longitude (decimal degrees)
    
    # Marketing content (JSONB)
    marketing_title = Column(String(255), nullable=True)  # Marketing title (e.g., "Two Bedroom Apartment in Binghatti Onyx")
    marketing_subtitle = Column(String(500), nullable=True)  # Marketing subtitle
    marketing_why = Column(JSONB, nullable=True)  # Why invest cards: [{"title": "...", "body": "..."}]
    marketing_highlights = Column(JSONB, nullable=True)  # Highlights: ["2 Bedrooms", "Pool", "Near Mall"]
    marketing_breakdown = Column(JSONB, nullable=True)  # Breakdown: {"purchase_cost": 173898.09, "transaction_cost": 25879.12, "running_cost": 38441.75}
    marketing_metrics = Column(JSONB, nullable=True)  # Metrics: {"gross_yield": 8.06, "net_yield": 6.01, "annualised_return": 12.96, "investors_count": 162, "days_left": 245}
    
    # Relationships
    investments = relationship("OfferInvestment", back_populates="offer", lazy="select")
    investment_intents = relationship("InvestmentIntent", back_populates="offer", lazy="select")
    
    # offer_media: all media attached to this offer via Media.offer_id
    # This is the ONLY ORM relationship between Offer and OfferMedia
    # CRITICAL: Use explicit foreign_keys to prevent SQLAlchemy from detecting cover_media_id and promo_video_media_id
    offer_media = relationship(
        "OfferMedia",
        foreign_keys="OfferMedia.offer_id",  # String reference to avoid circular import
        primaryjoin="Offer.id==OfferMedia.offer_id",
        cascade="all, delete-orphan",
        lazy="select",
        passive_deletes=True,
    )
    
    documents = relationship("OfferDocument", back_populates="offer", cascade="all, delete-orphan", lazy="select")
    
    # Many-to-many relationship with articles (via article_offers association table)
    # Note: article_offers table is defined in app.core.articles.models
    articles = relationship(
        "Article",
        secondary="article_offers",  # String reference to avoid circular import
        lazy="select",
        back_populates="offers",
    )
    
    # Timeline events (project progress)
    timeline_events = relationship(
        "OfferTimelineEvent",
        foreign_keys="OfferTimelineEvent.offer_id",
        primaryjoin="Offer.id==OfferTimelineEvent.offer_id",
        order_by="OfferTimelineEvent.sort_order.asc(), OfferTimelineEvent.occurred_at.asc().nullslast()",
        cascade="all, delete-orphan",
        lazy="select",
        back_populates="offer",
    )
    
    # Many-to-many relationship with partners (via partner_offers)
    partners = relationship(
        "Partner",
        secondary="partner_offers",  # String reference to avoid circular import
        lazy="select",
        back_populates="offers",
    )
    
    # Backward compatibility alias (deprecated, use offer_media instead)
    @property
    def media(self):
        """Backward compatibility: alias for offer_media"""
        return self.offer_media
    
    # PROPERTIES (not ORM relationships) for cover_media and promo_video_media
    # These avoid SQLAlchemy ambiguity by doing a simple lookup in offer_media
    @property
    def cover_media(self):
        """
        Get cover media by looking up cover_media_id in offer_media collection.
        Returns None if cover_media_id is not set or offer_media is not loaded.
        """
        if not self.cover_media_id:
            return None
        # If offer_media is not loaded, return None (we can't query without a session)
        if not hasattr(self, '_sa_instance_state') or 'offer_media' not in self._sa_instance_state.loaded_attrs:
            # Check if offer_media is actually loaded (not just lazy)
            if self.offer_media is None or (hasattr(self.offer_media, '__iter__') and not list(self.offer_media)):
                return None
        # Lookup in loaded offer_media collection
        if self.offer_media:
            return next((m for m in self.offer_media if m.id == self.cover_media_id), None)
        return None
    
    @property
    def promo_video_media(self):
        """
        Get promo video media by looking up promo_video_media_id in offer_media collection.
        Returns None if promo_video_media_id is not set or offer_media is not loaded.
        """
        if not self.promo_video_media_id:
            return None
        # If offer_media is not loaded, return None (we can't query without a session)
        if not hasattr(self, '_sa_instance_state') or 'offer_media' not in self._sa_instance_state.loaded_attrs:
            # Check if offer_media is actually loaded (not just lazy)
            if self.offer_media is None or (hasattr(self.offer_media, '__iter__') and not list(self.offer_media)):
                return None
        # Lookup in loaded offer_media collection
        if self.offer_media:
            return next((m for m in self.offer_media if m.id == self.promo_video_media_id), None)
        return None
    
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
    # offer: the offer this media belongs to (via Media.offer_id)
    # CRITICAL FIX: SQLAlchemy detects multiple foreign key paths:
    # 1. OfferMedia.offer_id -> Offer.id (the main relationship we want)
    # 2. Offer.cover_media_id -> OfferMedia.id (reverse FK, detected automatically)
    # 3. Offer.promo_video_media_id -> OfferMedia.id (reverse FK, detected automatically)
    #
    # SOLUTION: Use explicit foreign_keys to disambiguate. NO relationship for cover/promo.
    # We only define the ONE relationship: offer_media.offer_id -> offers.id
    offer = relationship(
        "Offer",
        back_populates="offer_media",
        foreign_keys=[offer_id],  # Explicit: use ONLY this column
        primaryjoin="OfferMedia.offer_id==Offer.id",  # Explicit join condition
    )
    
    # Note: cover_for_offers and promo_for_offers are not needed as backrefs
    # They would create ambiguity. Access via Offer.cover_media and Offer.promo_video_media instead.
    
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


class OfferTimelineEvent(BaseModel):
    """
    OfferTimelineEvent model - Represents a project progress update for an offer
    
    Features:
    - Native to an offer (not an article)
    - Optional link to an article for enrichment
    - Sortable by order and date
    - Short description (max 280 chars for UX)
    """
    
    __tablename__ = "offer_timeline_events"
    
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id", name="fk_offer_timeline_events_offer_id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(120), nullable=False)  # Short title
    description = Column(Text, nullable=False)  # Description (max 280 enforced via validation)
    occurred_at = Column(DateTime(timezone=True), nullable=True, index=True)  # When the event occurred (optional)
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id", name="fk_offer_timeline_events_article_id", ondelete="SET NULL"), nullable=True, index=True)  # Optional link to article
    sort_order = Column(Integer, nullable=False, default=0, index=True)  # Order for display
    
    # Relationships
    offer = relationship(
        "Offer",
        foreign_keys=[offer_id],
        primaryjoin="OfferTimelineEvent.offer_id==Offer.id",
        back_populates="timeline_events",
    )
    
    article = relationship(
        "Article",
        foreign_keys=[article_id],
        primaryjoin="OfferTimelineEvent.article_id==Article.id",
        lazy="select",
    )
    
    # Table-level constraints
    __table_args__ = (
        Index('idx_offer_timeline_offer_order', 'offer_id', 'sort_order'),
        CheckConstraint('sort_order >= 0', name='check_timeline_sort_order_non_negative'),
    )
