"""create_articles_tables

Revision ID: a1b2c3d4e5f7
Revises: f7e8d9c0b1a2
Create Date: 2025-12-20 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f7'
down_revision = 'f7e8d9c0b1a2'  # Last migration: add_offer_marketing_v1_1_fields
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create article_media_type enum
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'article_media_type') THEN
                CREATE TYPE article_media_type AS ENUM ('image', 'video', 'document');
            END IF;
        END $$;
    """)
    
    # Create articles table
    op.create_table(
        'articles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('subtitle', sa.String(500), nullable=True),
        sa.Column('excerpt', sa.Text(), nullable=True),
        sa.Column('content_markdown', sa.Text(), nullable=True),
        sa.Column('content_html', sa.Text(), nullable=True),
        sa.Column('cover_media_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('promo_video_media_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('author_name', sa.String(255), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('seo_title', sa.String(500), nullable=True),
        sa.Column('seo_description', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('allow_comments', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_articles')
    )
    
    # Create indexes for articles
    op.create_index('ix_articles_slug', 'articles', ['slug'], unique=True)
    op.create_index('ix_articles_status', 'articles', ['status'])
    op.create_index('ix_articles_published_at', 'articles', ['published_at'])
    op.create_index('ix_articles_is_featured', 'articles', ['is_featured'])
    op.create_index('ix_articles_cover_media_id', 'articles', ['cover_media_id'])
    op.create_index('ix_articles_promo_video_media_id', 'articles', ['promo_video_media_id'])
    op.create_index('idx_articles_status_published', 'articles', ['status', 'published_at'])
    op.create_index('idx_articles_featured_published', 'articles', ['is_featured', 'published_at'])
    
    # Create article_media table
    op.create_table(
        'article_media',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('article_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', postgresql.ENUM('image', 'video', 'document', name='article_media_type', create_type=False), nullable=False),
        sa.Column('key', sa.String(512), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('url', sa.String(1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], name='fk_article_media_article_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_article_media')
    )
    
    # Create indexes for article_media
    op.create_index('ix_article_media_article_id', 'article_media', ['article_id'])
    op.create_index('ix_article_media_type', 'article_media', ['type'])
    op.create_index('ix_article_media_key', 'article_media', ['key'], unique=True)
    op.create_index('idx_article_media_article_created', 'article_media', ['article_id', 'created_at'])
    
    # Add foreign key constraints for articles.cover_media_id and articles.promo_video_media_id
    op.create_foreign_key(
        'fk_articles_cover_media_id',
        'articles', 'article_media',
        ['cover_media_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_articles_promo_video_media_id',
        'articles', 'article_media',
        ['promo_video_media_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create article_offers association table (many-to-many)
    op.create_table(
        'article_offers',
        sa.Column('article_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('offer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], name='fk_article_offers_article_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['offer_id'], ['offers.id'], name='fk_article_offers_offer_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('article_id', 'offer_id', name='pk_article_offers')
    )
    
    # Create index for article_offers
    op.create_index('idx_article_offers_offer_id', 'article_offers', ['offer_id'])


def downgrade() -> None:
    # Drop article_offers table
    op.drop_index('idx_article_offers_offer_id', table_name='article_offers')
    op.drop_table('article_offers')
    
    # Drop foreign key constraints from articles to article_media
    op.drop_constraint('fk_articles_promo_video_media_id', 'articles', type_='foreignkey')
    op.drop_constraint('fk_articles_cover_media_id', 'articles', type_='foreignkey')
    
    # Drop article_media table
    op.drop_index('idx_article_media_article_created', table_name='article_media')
    op.drop_index('ix_article_media_key', table_name='article_media')
    op.drop_index('ix_article_media_type', table_name='article_media')
    op.drop_index('ix_article_media_article_id', table_name='article_media')
    op.drop_table('article_media')
    
    # Drop articles table
    op.drop_index('idx_articles_featured_published', table_name='articles')
    op.drop_index('idx_articles_status_published', table_name='articles')
    op.drop_index('ix_articles_promo_video_media_id', table_name='articles')
    op.drop_index('ix_articles_cover_media_id', table_name='articles')
    op.drop_index('ix_articles_is_featured', table_name='articles')
    op.drop_index('ix_articles_published_at', table_name='articles')
    op.drop_index('ix_articles_status', table_name='articles')
    op.drop_index('ix_articles_slug', table_name='articles')
    op.drop_table('articles')
    
    # Drop enum type
    op.execute("DROP TYPE IF EXISTS article_media_type")



