"""add_updated_at_to_partner_media_tables

Revision ID: 92427fb382a2
Revises: 2025_12_21_1200
Create Date: 2025-12-22 11:49:11.757082

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '92427fb382a2'
down_revision = '2025_12_21_1200'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add updated_at columns to partner media tables (missing from initial migration)
    op.add_column('partner_media', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('partner_documents', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('partner_portfolio_media', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove updated_at columns
    op.drop_column('partner_portfolio_media', 'updated_at')
    op.drop_column('partner_documents', 'updated_at')
    op.drop_column('partner_media', 'updated_at')



