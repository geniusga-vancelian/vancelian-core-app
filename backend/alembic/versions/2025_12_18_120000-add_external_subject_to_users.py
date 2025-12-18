"""Add external_subject to users table

Revision ID: add_external_subject
Revises: 
Create Date: 2025-12-18 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_external_subject'
down_revision = None  # This is the first migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add external_subject column to users table
    op.add_column(
        'users',
        sa.Column('external_subject', sa.String(255), nullable=True)
    )
    
    # Create regular index on external_subject (for lookups)
    op.create_index(
        'ix_users_external_subject',
        'users',
        ['external_subject']
    )
    
    # Create partial unique index for non-NULL values
    # This ensures uniqueness only when external_subject is not NULL
    # Allows multiple NULL values (users without OIDC subject yet)
    op.execute(
        """
        CREATE UNIQUE INDEX ix_users_external_subject_unique 
        ON users (external_subject) 
        WHERE external_subject IS NOT NULL
        """
    )


def downgrade() -> None:
    # Drop partial unique index
    op.drop_index('ix_users_external_subject_unique', table_name='users')
    
    # Drop regular index
    op.drop_index('ix_users_external_subject', table_name='users')
    
    # Drop column
    op.drop_column('users', 'external_subject')

