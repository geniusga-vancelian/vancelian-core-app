"""add_offer_media_and_documents_tables

Revision ID: 0c6c9cd4e9b7
Revises: 5caa0f83f45d
Create Date: 2025-12-19 18:40:56.401963

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = '0c6c9cd4e9b7'
down_revision = '5caa0f83f45d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create media_type enum
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'media_type') THEN
                CREATE TYPE media_type AS ENUM ('IMAGE', 'VIDEO');
            END IF;
        END $$;
    """)
    
    # Create media_visibility enum
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'media_visibility') THEN
                CREATE TYPE media_visibility AS ENUM ('PUBLIC', 'PRIVATE');
            END IF;
        END $$;
    """)
    
    # Create document_kind enum
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'document_kind') THEN
                CREATE TYPE document_kind AS ENUM ('BROCHURE', 'MEMO', 'PROJECTIONS', 'VALUATION', 'OTHER');
            END IF;
        END $$;
    """)
    
    # Create document_visibility enum
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'document_visibility') THEN
                CREATE TYPE document_visibility AS ENUM ('PUBLIC', 'PRIVATE');
            END IF;
        END $$;
    """)
    
    # Create offer_media table
    op.create_table(
        'offer_media',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('offer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', postgresql.ENUM('IMAGE', 'VIDEO', name='media_type', create_type=False), nullable=False),
        sa.Column('key', sa.String(512), nullable=False),
        sa.Column('url', sa.String(1024), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_cover', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('visibility', postgresql.ENUM('PUBLIC', 'PRIVATE', name='media_visibility', create_type=False), nullable=False, server_default='PUBLIC'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['offer_id'], ['offers.id'], name='fk_offer_media_offer_id'),
        sa.PrimaryKeyConstraint('id', name='pk_offer_media')
    )
    
    # Create indexes for offer_media
    op.create_index('ix_offer_media_offer_id', 'offer_media', ['offer_id'])
    op.create_index('ix_offer_media_type', 'offer_media', ['type'])
    op.create_index('ix_offer_media_key', 'offer_media', ['key'], unique=True)
    op.create_index('ix_offer_media_sort_order', 'offer_media', ['sort_order'])
    op.create_index('ix_offer_media_is_cover', 'offer_media', ['is_cover'])
    op.create_index('ix_offer_media_visibility', 'offer_media', ['visibility'])
    op.create_index('idx_offer_media_offer_sort', 'offer_media', ['offer_id', 'sort_order'])
    
    # Create check constraints for offer_media
    op.create_check_constraint(
        'check_media_size_positive',
        'offer_media',
        'size_bytes > 0'
    )
    op.create_check_constraint(
        'check_media_sort_order_non_negative',
        'offer_media',
        'sort_order >= 0'
    )
    
    # Create offer_documents table
    op.create_table(
        'offer_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('offer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('kind', postgresql.ENUM('BROCHURE', 'MEMO', 'PROJECTIONS', 'VALUATION', 'OTHER', name='document_kind', create_type=False), nullable=False),
        sa.Column('key', sa.String(512), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('visibility', postgresql.ENUM('PUBLIC', 'PRIVATE', name='document_visibility', create_type=False), nullable=False, server_default='PUBLIC'),
        sa.Column('url', sa.String(1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['offer_id'], ['offers.id'], name='fk_offer_documents_offer_id'),
        sa.PrimaryKeyConstraint('id', name='pk_offer_documents')
    )
    
    # Create indexes for offer_documents
    op.create_index('ix_offer_documents_offer_id', 'offer_documents', ['offer_id'])
    op.create_index('ix_offer_documents_kind', 'offer_documents', ['kind'])
    op.create_index('ix_offer_documents_key', 'offer_documents', ['key'], unique=True)
    op.create_index('ix_offer_documents_visibility', 'offer_documents', ['visibility'])
    
    # Create check constraint for offer_documents
    op.create_check_constraint(
        'check_document_size_positive',
        'offer_documents',
        'size_bytes > 0'
    )


def downgrade() -> None:
    # Drop tables
    op.drop_table('offer_documents')
    op.drop_table('offer_media')
    
    # Drop enums (only if no other tables use them)
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE udt_name = 'media_type'
            ) THEN
                DROP TYPE IF EXISTS media_type;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE udt_name = 'media_visibility'
            ) THEN
                DROP TYPE IF EXISTS media_visibility;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE udt_name = 'document_kind'
            ) THEN
                DROP TYPE IF EXISTS document_kind;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE udt_name = 'document_visibility'
            ) THEN
                DROP TYPE IF EXISTS document_visibility;
            END IF;
        END $$;
    """)
