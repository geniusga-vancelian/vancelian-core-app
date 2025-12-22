"""create offer_timeline_events table

Revision ID: 2025_12_20_1400
Revises: a1b2c3d4e5f7
Create Date: 2025-12-20 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2025_12_20_1400'
down_revision = 'a1b2c3d4e5f7'  # Last migration: create_articles_tables
branch_labels = None
depends_on = None


def upgrade():
    # Create offer_timeline_events table
    op.create_table(
        'offer_timeline_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('offer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=120), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('article_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['offer_id'], ['offers.id'], name='fk_offer_timeline_events_offer_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], name='fk_offer_timeline_events_article_id', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='pk_offer_timeline_events'),
        sa.CheckConstraint('sort_order >= 0', name='check_timeline_sort_order_non_negative'),
    )
    
    # Create indexes
    op.create_index('idx_offer_timeline_events_offer_id', 'offer_timeline_events', ['offer_id'])
    op.create_index('idx_offer_timeline_events_article_id', 'offer_timeline_events', ['article_id'])
    op.create_index('idx_offer_timeline_events_occurred_at', 'offer_timeline_events', ['occurred_at'])
    op.create_index('idx_offer_timeline_events_sort_order', 'offer_timeline_events', ['sort_order'])
    op.create_index('idx_offer_timeline_offer_order', 'offer_timeline_events', ['offer_id', 'sort_order'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_offer_timeline_offer_order', table_name='offer_timeline_events')
    op.drop_index('idx_offer_timeline_events_sort_order', table_name='offer_timeline_events')
    op.drop_index('idx_offer_timeline_events_occurred_at', table_name='offer_timeline_events')
    op.drop_index('idx_offer_timeline_events_article_id', table_name='offer_timeline_events')
    op.drop_index('idx_offer_timeline_events_offer_id', table_name='offer_timeline_events')
    
    # Drop table
    op.drop_table('offer_timeline_events')

