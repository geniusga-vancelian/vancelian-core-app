"""
Partner models - Trusted Partners with CEO module, team, portfolio, and media
"""

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, Text, DateTime, Index, Integer, BigInteger, Boolean, Table, Date, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum
from app.core.common.base_model import BaseModel
from app.infrastructure.database import Base


class PartnerStatus(str, enum.Enum):
    """Partner status enum"""
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class PartnerMediaType(str, enum.Enum):
    """Partner media type enum"""
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


class PartnerDocumentType(str, enum.Enum):
    """Partner document type enum"""
    PDF = "PDF"
    DOC = "DOC"
    OTHER = "OTHER"


class PartnerPortfolioProjectStatus(str, enum.Enum):
    """Portfolio project status enum"""
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


# Association table for many-to-many relationship between partners and offers
partner_offers = Table(
    'partner_offers',
    Base.metadata,
    Column('id', UUID(as_uuid=True), primary_key=True),
    Column('partner_id', UUID(as_uuid=True), ForeignKey('partners.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('offer_id', UUID(as_uuid=True), ForeignKey('offers.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('is_primary', Boolean, nullable=False, default=False, index=True),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default='now()'),
    Index('idx_partner_offers_partner_id', 'partner_id'),
    Index('idx_partner_offers_offer_id', 'offer_id'),
    Index('idx_partner_offers_unique', 'partner_id', 'offer_id', unique=True),
)


class Partner(BaseModel):
    """
    Partner model - Represents a trusted partner with CEO module, team, portfolio, and media
    
    Features:
    - Identity and contact information
    - CEO module (name, title, quote, bio, photo)
    - Team members
    - Portfolio projects (past projects)
    - Media gallery and documents
    - Linked offers (primary + additional)
    - Status workflow: DRAFT -> PUBLISHED -> ARCHIVED
    """
    
    __tablename__ = "partners"
    
    code = Column(String(100), unique=True, nullable=False, index=True)  # Unique slug-like code
    legal_name = Column(String(255), nullable=False)
    trade_name = Column(String(255), nullable=True)
    description_markdown = Column(Text, nullable=True)
    website_url = Column(String(500), nullable=True)
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    status = Column(SQLEnum(PartnerStatus, name="partner_status", create_constraint=True), nullable=False, default=PartnerStatus.DRAFT, index=True)
    
    # CEO module fields
    ceo_name = Column(String(255), nullable=True)
    ceo_title = Column(String(255), nullable=True)
    ceo_quote = Column(String(240), nullable=True)  # Max 240 chars
    ceo_bio_markdown = Column(Text, nullable=True)
    ceo_photo_media_id = Column(UUID(as_uuid=True), ForeignKey("partner_media.id", name="fk_partners_ceo_photo_media_id"), nullable=True, index=True)
    
    # Relationships
    # Partner media (images/videos) - explicit FK to avoid ambiguity
    partner_media = relationship(
        "PartnerMedia",
        foreign_keys="PartnerMedia.partner_id",
        primaryjoin="Partner.id==PartnerMedia.partner_id",
        cascade="all, delete-orphan",
        lazy="select",
        passive_deletes=True,
        back_populates="partner",
    )
    
    # Partner documents
    partner_documents = relationship(
        "PartnerDocument",
        foreign_keys="PartnerDocument.partner_id",
        primaryjoin="Partner.id==PartnerDocument.partner_id",
        cascade="all, delete-orphan",
        lazy="select",
        passive_deletes=True,
        back_populates="partner",
    )
    
    # Team members
    team_members = relationship(
        "PartnerTeamMember",
        foreign_keys="PartnerTeamMember.partner_id",
        primaryjoin="Partner.id==PartnerTeamMember.partner_id",
        cascade="all, delete-orphan",
        lazy="select",
        passive_deletes=True,
        order_by="PartnerTeamMember.sort_order.asc()",
        back_populates="partner",
    )
    
    # Portfolio projects
    portfolio_projects = relationship(
        "PartnerPortfolioProject",
        foreign_keys="PartnerPortfolioProject.partner_id",
        primaryjoin="Partner.id==PartnerPortfolioProject.partner_id",
        cascade="all, delete-orphan",
        lazy="select",
        passive_deletes=True,
        back_populates="partner",
    )
    
    # Many-to-many relationship with offers
    offers = relationship(
        "Offer",
        secondary=partner_offers,
        lazy="select",
        back_populates="partners",
    )
    
    @property
    def ceo_photo_media(self):
        """Get CEO photo media (property to avoid FK ambiguity)"""
        if not self.ceo_photo_media_id:
            return None
        for media in self.partner_media:
            if media.id == self.ceo_photo_media_id:
                return media
        return None


class PartnerTeamMember(BaseModel):
    """
    PartnerTeamMember model - Team member of a partner
    """
    
    __tablename__ = "partner_team_members"
    
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id", name="fk_partner_team_members_partner_id", ondelete="CASCADE"), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    role_title = Column(String(255), nullable=True)
    bio_markdown = Column(Text, nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    website_url = Column(String(500), nullable=True)
    photo_media_id = Column(UUID(as_uuid=True), ForeignKey("partner_media.id", name="fk_partner_team_members_photo_media_id"), nullable=True, index=True)
    sort_order = Column(Integer, nullable=False, default=0, index=True)
    
    # Relationships
    partner = relationship(
        "Partner",
        foreign_keys=[partner_id],
        primaryjoin="PartnerTeamMember.partner_id==Partner.id",
        back_populates="team_members",
    )
    
    @property
    def photo_media(self):
        """Get photo media (property to avoid FK ambiguity)"""
        if not self.photo_media_id or not self.partner:
            return None
        for media in self.partner.partner_media:
            if media.id == self.photo_media_id:
                return media
        return None


class PartnerMedia(BaseModel):
    """
    PartnerMedia model - Images and videos for a partner
    """
    
    __tablename__ = "partner_media"
    
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id", name="fk_partner_media_partner_id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(SQLEnum(PartnerMediaType, name="partner_media_type", create_constraint=True), nullable=False, index=True)
    key = Column(String(512), unique=True, nullable=False, index=True)  # S3/R2 object key
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    width = Column(Integer, nullable=True)  # For images/videos
    height = Column(Integer, nullable=True)
    duration_seconds = Column(Integer, nullable=True)  # For videos
    created_at = Column(DateTime(timezone=True), nullable=False, server_default='now()')
    
    # Relationships
    partner = relationship(
        "Partner",
        foreign_keys=[partner_id],
        primaryjoin="PartnerMedia.partner_id==Partner.id",
        back_populates="partner_media",
    )
    
    # Table-level constraints
    __table_args__ = (
        CheckConstraint('size_bytes > 0', name='check_partner_media_size_positive'),
    )


class PartnerDocument(BaseModel):
    """
    PartnerDocument model - Documents for a partner
    """
    
    __tablename__ = "partner_documents"
    
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id", name="fk_partner_documents_partner_id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    type = Column(SQLEnum(PartnerDocumentType, name="partner_document_type", create_constraint=True), nullable=False, index=True)
    key = Column(String(512), unique=True, nullable=False, index=True)  # S3/R2 object key
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default='now()')
    
    # Relationships
    partner = relationship(
        "Partner",
        foreign_keys=[partner_id],
        primaryjoin="PartnerDocument.partner_id==Partner.id",
        back_populates="partner_documents",
    )
    
    # Table-level constraints
    __table_args__ = (
        CheckConstraint('size_bytes > 0', name='check_partner_document_size_positive'),
    )


class PartnerPortfolioProject(BaseModel):
    """
    PartnerPortfolioProject model - Past projects in partner's portfolio
    """
    
    __tablename__ = "partner_portfolio_projects"
    
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id", name="fk_partner_portfolio_projects_partner_id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    location = Column(String(255), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    short_summary = Column(String(240), nullable=True)  # Max 240 chars
    description_markdown = Column(Text, nullable=True)
    results_kpis = Column(JSONB, nullable=True)  # Array of strings (max 12 items, each max 40 chars enforced via validation)
    status = Column(SQLEnum(PartnerPortfolioProjectStatus, name="partner_portfolio_project_status", create_constraint=True), nullable=False, default=PartnerPortfolioProjectStatus.DRAFT, index=True)
    cover_media_id = Column(UUID(as_uuid=True), ForeignKey("partner_portfolio_media.id", name="fk_partner_portfolio_projects_cover_media_id"), nullable=True, index=True)
    promo_video_media_id = Column(UUID(as_uuid=True), ForeignKey("partner_portfolio_media.id", name="fk_partner_portfolio_projects_promo_video_media_id"), nullable=True, index=True)
    
    # Relationships
    partner = relationship(
        "Partner",
        foreign_keys=[partner_id],
        primaryjoin="PartnerPortfolioProject.partner_id==Partner.id",
        back_populates="portfolio_projects",
    )
    
    portfolio_media = relationship(
        "PartnerPortfolioMedia",
        foreign_keys="PartnerPortfolioMedia.project_id",
        primaryjoin="PartnerPortfolioProject.id==PartnerPortfolioMedia.project_id",
        cascade="all, delete-orphan",
        lazy="select",
        passive_deletes=True,
        back_populates="project",
    )
    
    @property
    def cover_media(self):
        """Get cover media (property to avoid FK ambiguity)"""
        if not self.cover_media_id:
            return None
        for media in self.portfolio_media:
            if media.id == self.cover_media_id:
                return media
        return None
    
    @property
    def promo_video_media(self):
        """Get promo video media (property to avoid FK ambiguity)"""
        if not self.promo_video_media_id:
            return None
        for media in self.portfolio_media:
            if media.id == self.promo_video_media_id:
                return media
        return None


class PartnerPortfolioMedia(BaseModel):
    """
    PartnerPortfolioMedia model - Media for portfolio projects
    """
    
    __tablename__ = "partner_portfolio_media"
    
    project_id = Column(UUID(as_uuid=True), ForeignKey("partner_portfolio_projects.id", name="fk_partner_portfolio_media_project_id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(SQLEnum(PartnerMediaType, name="partner_portfolio_media_type", create_constraint=True, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    key = Column(String(512), unique=True, nullable=False, index=True)  # S3/R2 object key
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    duration_seconds = Column(Integer, nullable=True)  # For videos
    created_at = Column(DateTime(timezone=True), nullable=False, server_default='now()')
    
    # Relationships
    project = relationship(
        "PartnerPortfolioProject",
        foreign_keys=[project_id],
        primaryjoin="PartnerPortfolioMedia.project_id==PartnerPortfolioProject.id",
        back_populates="portfolio_media",
    )
    
    # Table-level constraints
    __table_args__ = (
        CheckConstraint('size_bytes > 0', name='check_portfolio_media_size_positive'),
    )

