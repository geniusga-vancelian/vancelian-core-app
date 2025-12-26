"""create_wallet_locks_table

Revision ID: create_wallet_locks_20250126
Revises: create_vaults_20251225
Create Date: 2025-01-26 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_wallet_locks_20250126'
down_revision = 'create_vaults_20251225'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create wallet_locks table
    op.create_table(
        'wallet_locks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='AED'),
        sa.Column('amount', sa.Numeric(20, 2), nullable=False),
        sa.Column('reason', sa.String(length=50), nullable=False),
        sa.Column('reference_type', sa.String(length=20), nullable=False),
        sa.Column('reference_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('intent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('operation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_wallet_locks_user_id'),
        sa.ForeignKeyConstraint(['intent_id'], ['investment_intents.id'], name='fk_wallet_locks_intent_id'),
        sa.ForeignKeyConstraint(['operation_id'], ['operations.id'], name='fk_wallet_locks_operation_id'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('amount > 0', name='check_wallet_locks_amount_positive'),
        sa.UniqueConstraint('intent_id', name='uq_wallet_locks_intent_id'),
    )
    
    # Create indexes
    op.create_index(op.f('ix_wallet_locks_id'), 'wallet_locks', ['id'], unique=False)
    op.create_index(op.f('ix_wallet_locks_user_id'), 'wallet_locks', ['user_id'], unique=False)
    op.create_index(op.f('ix_wallet_locks_currency'), 'wallet_locks', ['currency'], unique=False)
    op.create_index(op.f('ix_wallet_locks_reason'), 'wallet_locks', ['reason'], unique=False)
    op.create_index(op.f('ix_wallet_locks_reference_type'), 'wallet_locks', ['reference_type'], unique=False)
    op.create_index(op.f('ix_wallet_locks_reference_id'), 'wallet_locks', ['reference_id'], unique=False)
    op.create_index(op.f('ix_wallet_locks_status'), 'wallet_locks', ['status'], unique=False)
    op.create_index(op.f('ix_wallet_locks_intent_id'), 'wallet_locks', ['intent_id'], unique=True)
    op.create_index(op.f('ix_wallet_locks_operation_id'), 'wallet_locks', ['operation_id'], unique=False)
    op.create_index('ix_wallet_locks_reference', 'wallet_locks', ['reference_type', 'reference_id', 'reason', 'status'], unique=False)
    op.create_index('ix_wallet_locks_user_status', 'wallet_locks', ['user_id', 'status'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_wallet_locks_user_status', table_name='wallet_locks')
    op.drop_index('ix_wallet_locks_reference', table_name='wallet_locks')
    op.drop_index(op.f('ix_wallet_locks_operation_id'), table_name='wallet_locks')
    op.drop_index(op.f('ix_wallet_locks_intent_id'), table_name='wallet_locks')
    op.drop_index(op.f('ix_wallet_locks_status'), table_name='wallet_locks')
    op.drop_index(op.f('ix_wallet_locks_reference_id'), table_name='wallet_locks')
    op.drop_index(op.f('ix_wallet_locks_reference_type'), table_name='wallet_locks')
    op.drop_index(op.f('ix_wallet_locks_reason'), table_name='wallet_locks')
    op.drop_index(op.f('ix_wallet_locks_currency'), table_name='wallet_locks')
    op.drop_index(op.f('ix_wallet_locks_user_id'), table_name='wallet_locks')
    op.drop_index(op.f('ix_wallet_locks_id'), table_name='wallet_locks')
    
    # Drop table
    op.drop_table('wallet_locks')

