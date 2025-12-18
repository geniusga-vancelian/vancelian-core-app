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
    # Create users table if it doesn't exist (initial migration)
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'SUSPENDED', name='user_status', create_constraint=True), nullable=False, server_default='ACTIVE'),
        sa.Column('external_subject', sa.String(255), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('first_name', sa.String(255), nullable=True),
        sa.Column('last_name', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_external_subject', 'users', ['external_subject'])
    
    # Create partial unique index for non-NULL external_subject values
    op.execute(
        """
        CREATE UNIQUE INDEX ix_users_external_subject_unique 
        ON users (external_subject) 
        WHERE external_subject IS NOT NULL
        """
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_users_external_subject_unique', table_name='users')
    op.drop_index('ix_users_external_subject', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_id', table_name='users')
    
    # Drop table
    op.drop_table('users')



