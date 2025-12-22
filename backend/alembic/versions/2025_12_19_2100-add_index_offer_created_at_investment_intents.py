"""add_index_offer_created_at_investment_intents

Revision ID: a1b2c3d4e5f6
Revises: bbe9f323dd0d
Create Date: 2025-12-19 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'bbe9f323dd0d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add composite index on (offer_id, created_at) for efficient ORDER BY created_at DESC queries
    op.create_index(
        'idx_investment_intents_offer_created_at',
        'investment_intents',
        ['offer_id', 'created_at'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('idx_investment_intents_offer_created_at', table_name='investment_intents')

