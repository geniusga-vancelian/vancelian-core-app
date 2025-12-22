"""
Article models - Blog/News articles with media and offer linkages
"""

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, Text, DateTime, Index, Integer, BigInteger, Boolean, Table
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum
from app.core.common.base_model import BaseModel
from app.infrastructure.database import Base


class ArticleStatus(str, enum.Enum):
    """Article status enum"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ArticleMediaType(str, enum.Enum):
    """Article media type enum"""
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"


# Association table for many-to-many relationship between articles and offers
# Note: Must use Base.metadata (not BaseModel.metadata) for table definition
article_offers = Table(
    'article_offers',
    Base.metadata,
    Column('article_id', UUID(as_uuid=True), ForeignKey('articles.id', ondelete='CASCADE'), primary_key=True),
    Column('offer_id', UUID(as_uuid=True), ForeignKey('offers.id', ondelete='CASCADE'), primary_key=True),
    Index('idx_article_offers_offer_id', 'offer_id'),
)


class Article(BaseModel):
    """
    Article model - Represents blog/news articles with rich content
    
    Features:
    - Slug-based routing (unique, indexed)
    - Status workflow: draft -> published -> archived
    - Markdown content with optional HTML pre-rendering
    - SEO fields (title, description)
    - Featured flag for homepage/blog hero
    - Many-to-many relationship with offers (via article_offers)
    - Media support (cover, promo video, gallery)
    """
    
    __tablename__ = "articles"
    
    slug = Column(String(255), unique=True, nullable=False, index=True)  # URL-friendly slug
    status = Column(String(20), nullable=False, default=ArticleStatus.DRAFT.value, index=True)  # draft, published, archived
    title = Column(String(500), nullable=False)  # Article title
    subtitle = Column(String(500), nullable=True)  # Optional subtitle
    excerpt = Column(Text, nullable=True)  # Short summary for cards
    content_markdown = Column(Text, nullable=True)  # Main content in markdown
    content_html = Column(Text, nullable=True)  # Optional pre-rendered HTML
    cover_media_id = Column(UUID(as_uuid=True), ForeignKey("article_media.id", name="fk_articles_cover_media_id"), nullable=True, index=True)
    promo_video_media_id = Column(UUID(as_uuid=True), ForeignKey("article_media.id", name="fk_articles_promo_video_media_id"), nullable=True, index=True)
    author_name = Column(String(255), nullable=True)  # Author name
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Publication timestamp
    seo_title = Column(String(500), nullable=True)  # SEO title (defaults to title if null)
    seo_description = Column(Text, nullable=True)  # SEO description
    tags = Column(JSONB, nullable=False, server_default='[]')  # Array of tag strings
    is_featured = Column(Boolean, nullable=False, default=False, index=True)  # Featured flag
    allow_comments = Column(Boolean, nullable=False, default=False)  # Comments flag (V1: not used but ready)
    
    # Relationships
    # article_media: all media attached to this article via ArticleMedia.article_id
    # CRITICAL: Use explicit foreign_keys to prevent SQLAlchemy ambiguity (same pattern as OfferMedia)
    article_media = relationship(
        "ArticleMedia",
        foreign_keys="ArticleMedia.article_id",
        primaryjoin="Article.id==ArticleMedia.article_id",
        cascade="all, delete-orphan",
        lazy="select",
        passive_deletes=True,
        back_populates="article",
    )
    
    # Many-to-many relationship with offers via association table
    offers = relationship(
        "Offer",
        secondary=article_offers,
        lazy="select",
        back_populates="articles",  # Will add this to Offer model
    )
    
    # Table-level constraints
    __table_args__ = (
        Index('idx_articles_status_published', 'status', 'published_at'),
        Index('idx_articles_featured_published', 'is_featured', 'published_at'),
    )
    
    # PROPERTIES (not ORM relationships) for cover_media and promo_video_media
    # These avoid SQLAlchemy ambiguity by doing a simple lookup in article_media
    @property
    def cover_media(self):
        """
        Get cover media by looking up cover_media_id in article_media collection.
        Returns None if cover_media_id is not set or article_media is not loaded.
        """
        if not self.cover_media_id:
            return None
        if self.article_media:
            return next((m for m in self.article_media if m.id == self.cover_media_id), None)
        return None
    
    @property
    def promo_video_media(self):
        """
        Get promo video media by looking up promo_video_media_id in article_media collection.
        Returns None if promo_video_media_id is not set or article_media is not loaded.
        """
        if not self.promo_video_media_id:
            return None
        if self.article_media:
            return next((m for m in self.article_media if m.id == self.promo_video_media_id), None)
        return None


class ArticleMedia(BaseModel):
    """
    ArticleMedia model - Represents media files (images/videos/documents) for articles stored in S3/R2
    
    Features:
    - Stores metadata only (actual file in S3/R2)
    - Supports presigned URLs for upload/download
    - Similar structure to OfferMedia
    """
    
    __tablename__ = "article_media"
    
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id", name="fk_article_media_article_id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(SQLEnum(ArticleMediaType, name="article_media_type", create_constraint=True, values_callable=lambda obj: [e.value for e in obj]), nullable=False, index=True)  # image, video, document
    key = Column(String(512), unique=True, nullable=False, index=True)  # S3/R2 object key
    mime_type = Column(String(100), nullable=False)  # e.g., image/jpeg, video/mp4, application/pdf
    size_bytes = Column(BigInteger, nullable=False)
    width = Column(Integer, nullable=True)  # For images/videos
    height = Column(Integer, nullable=True)  # For images/videos
    duration_seconds = Column(Integer, nullable=True)  # For videos
    url = Column(String(1024), nullable=True)  # Optional public CDN URL
    
    # Relationships
    # CRITICAL: Use explicit foreign_keys to disambiguate (same pattern as OfferMedia)
    article = relationship(
        "Article",
        foreign_keys=[article_id],
        primaryjoin="ArticleMedia.article_id==Article.id",
        back_populates="article_media",
    )
    
    # Table-level constraints
    __table_args__ = (
        Index('idx_article_media_article_created', 'article_id', 'created_at'),
    )

