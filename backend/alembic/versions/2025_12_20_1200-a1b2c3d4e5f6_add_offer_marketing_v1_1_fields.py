"""add_offer_marketing_v1_1_fields

Revision ID: f7e8d9c0b1a2
Revises: a1b2c3d4e5f6
Create Date: 2025-12-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f7e8d9c0b1a2'
down_revision = '0c6c9cd4e9b7'  # Last migration: add_offer_media_and_documents_tables
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add marketing V1.1 fields to offers table
    op.add_column('offers', sa.Column('cover_media_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('offers', sa.Column('promo_video_media_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('offers', sa.Column('location_label', sa.String(255), nullable=True))
    op.add_column('offers', sa.Column('location_lat', sa.Numeric(10, 7), nullable=True))
    op.add_column('offers', sa.Column('location_lng', sa.Numeric(10, 7), nullable=True))
    op.add_column('offers', sa.Column('marketing_title', sa.String(255), nullable=True))
    op.add_column('offers', sa.Column('marketing_subtitle', sa.String(500), nullable=True))
    op.add_column('offers', sa.Column('marketing_why', postgresql.JSONB, nullable=True))
    op.add_column('offers', sa.Column('marketing_highlights', postgresql.JSONB, nullable=True))
    op.add_column('offers', sa.Column('marketing_breakdown', postgresql.JSONB, nullable=True))
    op.add_column('offers', sa.Column('marketing_metrics', postgresql.JSONB, nullable=True))
    
    # Add foreign key constraints
    op.create_foreign_key(
        'fk_offers_cover_media_id',
        'offers', 'offer_media',
        ['cover_media_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_offers_promo_video_media_id',
        'offers', 'offer_media',
        ['promo_video_media_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Add indexes
    op.create_index('ix_offers_cover_media_id', 'offers', ['cover_media_id'])
    op.create_index('ix_offers_promo_video_media_id', 'offers', ['promo_video_media_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_offers_promo_video_media_id', table_name='offers')
    op.drop_index('ix_offers_cover_media_id', table_name='offers')
    
    # Drop foreign key constraints
    op.drop_constraint('fk_offers_promo_video_media_id', 'offers', type_='foreignkey')
    op.drop_constraint('fk_offers_cover_media_id', 'offers', type_='foreignkey')
    
    # Drop columns
    op.drop_column('offers', 'marketing_metrics')
    op.drop_column('offers', 'marketing_breakdown')
    op.drop_column('offers', 'marketing_highlights')
    op.drop_column('offers', 'marketing_why')
    op.drop_column('offers', 'marketing_subtitle')
    op.drop_column('offers', 'marketing_title')
    op.drop_column('offers', 'location_lng')
    op.drop_column('offers', 'location_lat')
    op.drop_column('offers', 'location_label')
    op.drop_column('offers', 'promo_video_media_id')
    op.drop_column('offers', 'cover_media_id')

