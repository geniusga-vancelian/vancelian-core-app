"""create partners tables

Revision ID: 2025_12_21_1200
Revises: 2025_12_20_1400
Create Date: 2025-12-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2025_12_21_1200'
down_revision = '2025_12_20_1400'  # Last migration: create_offer_timeline_events
branch_labels = None
depends_on = None


def upgrade():
    # Create partners table (enums will be created automatically by SQLAlchemy)
    op.create_table(
        'partners',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('legal_name', sa.String(length=255), nullable=False),
        sa.Column('trade_name', sa.String(length=255), nullable=True),
        sa.Column('description_markdown', sa.Text(), nullable=True),
        sa.Column('website_url', sa.String(length=500), nullable=True),
        sa.Column('address_line1', sa.String(length=255), nullable=True),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('status', sa.Enum('DRAFT', 'PUBLISHED', 'ARCHIVED', name='partner_status', create_type=True), nullable=False, server_default='DRAFT'),
        sa.Column('ceo_name', sa.String(length=255), nullable=True),
        sa.Column('ceo_title', sa.String(length=255), nullable=True),
        sa.Column('ceo_quote', sa.String(length=240), nullable=True),
        sa.Column('ceo_bio_markdown', sa.Text(), nullable=True),
        sa.Column('ceo_photo_media_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_partners'),
    )
    op.create_index('idx_partners_code', 'partners', ['code'], unique=True)
    op.create_index('idx_partners_status', 'partners', ['status'])
    op.create_index('idx_partners_ceo_photo_media_id', 'partners', ['ceo_photo_media_id'])
    
    # Create partner_media table (after partners table exists)
    op.create_table(
        'partner_media',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('partner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.Enum('IMAGE', 'VIDEO', name='partner_media_type'), nullable=False),
        sa.Column('key', sa.String(length=512), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['partner_id'], ['partners.id'], name='fk_partner_media_partner_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_partner_media'),
        sa.CheckConstraint('size_bytes > 0', name='check_partner_media_size_positive'),
        sa.UniqueConstraint('key', name='uq_partner_media_key'),
    )
    op.create_index('idx_partner_media_partner_id', 'partner_media', ['partner_id'])
    op.create_index('idx_partner_media_type', 'partner_media', ['type'])
    op.create_index('idx_partner_media_key', 'partner_media', ['key'], unique=True)
    
    # Add FK for partners.ceo_photo_media_id
    op.create_foreign_key(
        'fk_partners_ceo_photo_media_id',
        'partners', 'partner_media',
        ['ceo_photo_media_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create partner_documents table
    op.create_table(
        'partner_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('partner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('type', sa.Enum('PDF', 'DOC', 'OTHER', name='partner_document_type', create_type=True), nullable=False),
        sa.Column('key', sa.String(length=512), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['partner_id'], ['partners.id'], name='fk_partner_documents_partner_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_partner_documents'),
        sa.CheckConstraint('size_bytes > 0', name='check_partner_document_size_positive'),
        sa.UniqueConstraint('key', name='uq_partner_documents_key'),
    )
    op.create_index('idx_partner_documents_partner_id', 'partner_documents', ['partner_id'])
    op.create_index('idx_partner_documents_type', 'partner_documents', ['type'])
    
    # Create partner_team_members table
    op.create_table(
        'partner_team_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('partner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('role_title', sa.String(length=255), nullable=True),
        sa.Column('bio_markdown', sa.Text(), nullable=True),
        sa.Column('linkedin_url', sa.String(length=500), nullable=True),
        sa.Column('website_url', sa.String(length=500), nullable=True),
        sa.Column('photo_media_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['partner_id'], ['partners.id'], name='fk_partner_team_members_partner_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['photo_media_id'], ['partner_media.id'], name='fk_partner_team_members_photo_media_id', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='pk_partner_team_members'),
    )
    op.create_index('idx_partner_team_members_partner_id', 'partner_team_members', ['partner_id'])
    op.create_index('idx_partner_team_members_sort_order', 'partner_team_members', ['sort_order'])
    op.create_index('idx_partner_team_members_photo_media_id', 'partner_team_members', ['photo_media_id'])
    
    # Create partner_portfolio_projects table
    op.create_table(
        'partner_portfolio_projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('partner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('short_summary', sa.String(length=240), nullable=True),
        sa.Column('description_markdown', sa.Text(), nullable=True),
        sa.Column('results_kpis', postgresql.JSONB, nullable=True),
        sa.Column('status', sa.Enum('DRAFT', 'PUBLISHED', 'ARCHIVED', name='partner_portfolio_project_status', create_type=True), nullable=False, server_default='DRAFT'),
        sa.Column('cover_media_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('promo_video_media_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['partner_id'], ['partners.id'], name='fk_partner_portfolio_projects_partner_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_partner_portfolio_projects'),
    )
    op.create_index('idx_partner_portfolio_projects_partner_id', 'partner_portfolio_projects', ['partner_id'])
    op.create_index('idx_partner_portfolio_projects_status', 'partner_portfolio_projects', ['status'])
    op.create_index('idx_partner_portfolio_projects_partner_status', 'partner_portfolio_projects', ['partner_id', 'status'])
    
    # Create partner_portfolio_media table
    op.create_table(
        'partner_portfolio_media',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.Enum('IMAGE', 'VIDEO', name='partner_portfolio_media_type', create_type=True), nullable=False),
        sa.Column('key', sa.String(length=512), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['partner_portfolio_projects.id'], name='fk_partner_portfolio_media_project_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_partner_portfolio_media'),
        sa.CheckConstraint('size_bytes > 0', name='check_portfolio_media_size_positive'),
        sa.UniqueConstraint('key', name='uq_partner_portfolio_media_key'),
    )
    op.create_index('idx_partner_portfolio_media_project_id', 'partner_portfolio_media', ['project_id'])
    op.create_index('idx_partner_portfolio_media_type', 'partner_portfolio_media', ['type'])
    
    # Add FKs for portfolio project cover and promo video
    op.create_foreign_key(
        'fk_partner_portfolio_projects_cover_media_id',
        'partner_portfolio_projects', 'partner_portfolio_media',
        ['cover_media_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_partner_portfolio_projects_promo_video_media_id',
        'partner_portfolio_projects', 'partner_portfolio_media',
        ['promo_video_media_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('idx_partner_portfolio_projects_cover_media_id', 'partner_portfolio_projects', ['cover_media_id'])
    op.create_index('idx_partner_portfolio_projects_promo_video_media_id', 'partner_portfolio_projects', ['promo_video_media_id'])
    
    # Create partner_offers join table
    op.create_table(
        'partner_offers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('partner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('offer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['partner_id'], ['partners.id'], name='fk_partner_offers_partner_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['offer_id'], ['offers.id'], name='fk_partner_offers_offer_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_partner_offers'),
        sa.UniqueConstraint('partner_id', 'offer_id', name='uq_partner_offers_partner_offer'),
    )
    op.create_index('idx_partner_offers_partner_id', 'partner_offers', ['partner_id'])
    op.create_index('idx_partner_offers_offer_id', 'partner_offers', ['offer_id'])
    op.create_index('idx_partner_offers_is_primary', 'partner_offers', ['is_primary'])


def downgrade():
    # Drop partner_offers table
    op.drop_index('idx_partner_offers_is_primary', table_name='partner_offers')
    op.drop_index('idx_partner_offers_offer_id', table_name='partner_offers')
    op.drop_index('idx_partner_offers_partner_id', table_name='partner_offers')
    op.drop_table('partner_offers')
    
    # Drop portfolio media FKs and indexes
    op.drop_index('idx_partner_portfolio_projects_promo_video_media_id', table_name='partner_portfolio_projects')
    op.drop_index('idx_partner_portfolio_projects_cover_media_id', table_name='partner_portfolio_projects')
    op.drop_foreign_key('fk_partner_portfolio_projects_promo_video_media_id', 'partner_portfolio_projects')
    op.drop_foreign_key('fk_partner_portfolio_projects_cover_media_id', 'partner_portfolio_projects')
    
    # Drop partner_portfolio_media table
    op.drop_index('idx_partner_portfolio_media_type', table_name='partner_portfolio_media')
    op.drop_index('idx_partner_portfolio_media_project_id', table_name='partner_portfolio_media')
    op.drop_table('partner_portfolio_media')
    
    # Drop partner_portfolio_projects table
    op.drop_index('idx_partner_portfolio_projects_partner_status', table_name='partner_portfolio_projects')
    op.drop_index('idx_partner_portfolio_projects_status', table_name='partner_portfolio_projects')
    op.drop_index('idx_partner_portfolio_projects_partner_id', table_name='partner_portfolio_projects')
    op.drop_table('partner_portfolio_projects')
    
    # Drop partner_team_members table
    op.drop_index('idx_partner_team_members_photo_media_id', table_name='partner_team_members')
    op.drop_index('idx_partner_team_members_sort_order', table_name='partner_team_members')
    op.drop_index('idx_partner_team_members_partner_id', table_name='partner_team_members')
    op.drop_table('partner_team_members')
    
    # Drop partner_documents table
    op.drop_index('idx_partner_documents_type', table_name='partner_documents')
    op.drop_index('idx_partner_documents_partner_id', table_name='partner_documents')
    op.drop_table('partner_documents')
    
    # Drop partners table FK and then partner_media
    op.drop_foreign_key('fk_partners_ceo_photo_media_id', 'partners')
    
    # Drop partner_media table
    op.drop_index('idx_partner_media_key', table_name='partner_media')
    op.drop_index('idx_partner_media_type', table_name='partner_media')
    op.drop_index('idx_partner_media_partner_id', table_name='partner_media')
    op.drop_table('partner_media')
    
    # Drop partners table
    op.drop_index('idx_partners_ceo_photo_media_id', table_name='partners')
    op.drop_index('idx_partners_status', table_name='partners')
    op.drop_index('idx_partners_code', table_name='partners')
    op.drop_table('partners')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS partner_portfolio_project_status")
    op.execute("DROP TYPE IF EXISTS partner_document_type")
    op.execute("DROP TYPE IF EXISTS partner_media_type")
    op.execute("DROP TYPE IF EXISTS partner_status")

