"""create_vault_vesting_lots_table

Revision ID: create_vault_vesting_lots_20250127
Revises: 7e6c633bb443
Create Date: 2025-01-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_vault_vesting_lots_20250127'
down_revision = '7e6c633bb443'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create vault_vesting_lots table
    op.create_table(
        'vault_vesting_lots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('vault_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vault_code', sa.String(length=50), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='AED'),
        sa.Column('deposit_day', sa.Date(), nullable=False),
        sa.Column('release_day', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(20, 2), nullable=False),
        sa.Column('released_amount', sa.Numeric(20, 2), nullable=False, server_default='0.00'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='VESTED'),
        sa.Column('source_operation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('last_released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_release_operation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('release_job_trace_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('release_job_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['vault_id'], ['vaults.id'], name='fk_vault_vesting_lots_vault_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_vault_vesting_lots_user_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_operation_id'], ['operations.id'], name='fk_vault_vesting_lots_source_operation_id'),
        sa.ForeignKeyConstraint(['last_release_operation_id'], ['operations.id'], name='fk_vault_vesting_lots_last_release_operation_id'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('amount > 0', name='ck_vault_vesting_lots_amount_positive'),
        sa.CheckConstraint('released_amount >= 0 AND released_amount <= amount', name='ck_vault_vesting_lots_released_amount_valid'),
        sa.CheckConstraint(
            "(status = 'RELEASED' AND released_amount = amount) OR (status != 'RELEASED')",
            name='ck_vault_vesting_lots_status_released'
        ),
        sa.UniqueConstraint('source_operation_id', name='uq_vault_vesting_lots_source_operation'),
    )
    
    # Create indexes
    op.create_index(op.f('ix_vault_vesting_lots_id'), 'vault_vesting_lots', ['id'], unique=False)
    op.create_index(op.f('ix_vault_vesting_lots_vault_id'), 'vault_vesting_lots', ['vault_id'], unique=False)
    op.create_index(op.f('ix_vault_vesting_lots_vault_code'), 'vault_vesting_lots', ['vault_code'], unique=False)
    op.create_index(op.f('ix_vault_vesting_lots_user_id'), 'vault_vesting_lots', ['user_id'], unique=False)
    op.create_index(op.f('ix_vault_vesting_lots_currency'), 'vault_vesting_lots', ['currency'], unique=False)
    op.create_index(op.f('ix_vault_vesting_lots_status'), 'vault_vesting_lots', ['status'], unique=False)
    op.create_index(op.f('ix_vault_vesting_lots_source_operation_id'), 'vault_vesting_lots', ['source_operation_id'], unique=True)
    op.create_index('ix_vault_vesting_lots_vault_user', 'vault_vesting_lots', ['vault_id', 'user_id'], unique=False)
    op.create_index('ix_vault_vesting_lots_release_day_status', 'vault_vesting_lots', ['release_day', 'status'], unique=False)
    op.create_index('ix_vault_vesting_lots_user_status', 'vault_vesting_lots', ['user_id', 'status'], unique=False)
    op.create_index('ix_vault_vesting_lots_vault_code_release_day', 'vault_vesting_lots', ['vault_code', 'release_day', 'status'], unique=False)
    
    # Create generated column for remaining_amount (PostgreSQL 12+)
    # Note: This is a computed column, stored for performance
    op.execute("""
        ALTER TABLE vault_vesting_lots
        ADD COLUMN remaining_amount NUMERIC(20, 2) 
        GENERATED ALWAYS AS (amount - released_amount) STORED;
    """)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_vault_vesting_lots_vault_code_release_day', table_name='vault_vesting_lots')
    op.drop_index('ix_vault_vesting_lots_user_status', table_name='vault_vesting_lots')
    op.drop_index('ix_vault_vesting_lots_release_day_status', table_name='vault_vesting_lots')
    op.drop_index('ix_vault_vesting_lots_vault_user', table_name='vault_vesting_lots')
    op.drop_index(op.f('ix_vault_vesting_lots_source_operation_id'), table_name='vault_vesting_lots')
    op.drop_index(op.f('ix_vault_vesting_lots_status'), table_name='vault_vesting_lots')
    op.drop_index(op.f('ix_vault_vesting_lots_currency'), table_name='vault_vesting_lots')
    op.drop_index(op.f('ix_vault_vesting_lots_user_id'), table_name='vault_vesting_lots')
    op.drop_index(op.f('ix_vault_vesting_lots_vault_code'), table_name='vault_vesting_lots')
    op.drop_index(op.f('ix_vault_vesting_lots_vault_id'), table_name='vault_vesting_lots')
    op.drop_index(op.f('ix_vault_vesting_lots_id'), table_name='vault_vesting_lots')
    
    # Drop table (remaining_amount column will be dropped automatically)
    op.drop_table('vault_vesting_lots')

