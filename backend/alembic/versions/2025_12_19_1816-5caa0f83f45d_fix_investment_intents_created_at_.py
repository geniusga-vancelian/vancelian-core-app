"""fix_investment_intents_created_at_default

Revision ID: 5caa0f83f45d
Revises: bbe9f323dd0d
Create Date: 2025-12-19 18:16:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = '5caa0f83f45d'
down_revision = 'a1b2c3d4e5f6'  # After add_index_offer_created_at_investment_intents
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add server_default to created_at column in investment_intents table
    # This ensures created_at is automatically set by the database when a row is inserted
    op.alter_column(
        'investment_intents',
        'created_at',
        server_default=func.now(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False
    )


def downgrade() -> None:
    # Remove server_default from created_at column
    op.alter_column(
        'investment_intents',
        'created_at',
        server_default=None,
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False
    )
