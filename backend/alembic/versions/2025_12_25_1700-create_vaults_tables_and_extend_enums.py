"""create_vaults_tables_and_extend_enums

Revision ID: create_vaults_20251225
Revises: 92427fb382a2
Create Date: 2025-12-25 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_vaults_20251225'
down_revision = '92427fb382a2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Add new enum values to operation_type enum
    # Check if enum values already exist (idempotent)
    op.execute("""
        DO $$ 
        BEGIN
            -- Add VAULT_DEPOSIT if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'VAULT_DEPOSIT' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'operation_type')
            ) THEN
                ALTER TYPE operation_type ADD VALUE 'VAULT_DEPOSIT';
            END IF;
            
            -- Add VAULT_WITHDRAW_EXECUTED if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'VAULT_WITHDRAW_EXECUTED' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'operation_type')
            ) THEN
                ALTER TYPE operation_type ADD VALUE 'VAULT_WITHDRAW_EXECUTED';
            END IF;
        END $$;
    """)
    
    # Step 2: Add new enum value to account_type enum
    op.execute("""
        DO $$ 
        BEGIN
            -- Add VAULT_POOL_CASH if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'VAULT_POOL_CASH' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'account_type')
            ) THEN
                ALTER TYPE account_type ADD VALUE 'VAULT_POOL_CASH';
            END IF;
        END $$;
    """)
    
    # Step 3: Create vault_status enum
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vault_status') THEN
                CREATE TYPE vault_status AS ENUM ('ACTIVE', 'PAUSED', 'CLOSED');
            END IF;
        END $$;
    """)
    
    # Step 4: Create withdrawal_request_status enum
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'withdrawal_request_status') THEN
                CREATE TYPE withdrawal_request_status AS ENUM ('PENDING', 'EXECUTED', 'CANCELLED');
            END IF;
        END $$;
    """)
    
    # Step 5: Create vaults table
    op.create_table(
        'vaults',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', postgresql.ENUM('ACTIVE', 'PAUSED', 'CLOSED', name='vault_status', create_type=False), nullable=False, server_default='ACTIVE'),
        sa.Column('cash_balance', sa.Numeric(20, 2), nullable=False, server_default='0.00'),
        sa.Column('total_aum', sa.Numeric(20, 2), nullable=False, server_default='0.00'),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_vaults_id'), 'vaults', ['id'], unique=False)
    op.create_index(op.f('ix_vaults_code'), 'vaults', ['code'], unique=True)
    op.create_index(op.f('ix_vaults_status'), 'vaults', ['status'], unique=False)
    
    # Step 6: Create vault_accounts table
    op.create_table(
        'vault_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('vault_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('principal', sa.Numeric(20, 2), nullable=False, server_default='0.00'),
        sa.Column('available_balance', sa.Numeric(20, 2), nullable=False, server_default='0.00'),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['vault_id'], ['vaults.id'], name='fk_vault_accounts_vault_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_vault_accounts_user_id'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vault_id', 'user_id', name='uq_vault_accounts_vault_user'),
    )
    op.create_index(op.f('ix_vault_accounts_id'), 'vault_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_vault_accounts_vault_id'), 'vault_accounts', ['vault_id'], unique=False)
    op.create_index(op.f('ix_vault_accounts_user_id'), 'vault_accounts', ['user_id'], unique=False)
    op.create_index('ix_vault_accounts_vault_user', 'vault_accounts', ['vault_id', 'user_id'], unique=False)
    
    # Step 7: Create withdrawal_requests table
    op.create_table(
        'withdrawal_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('vault_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(20, 2), nullable=False),
        sa.Column('status', postgresql.ENUM('PENDING', 'EXECUTED', 'CANCELLED', name='withdrawal_request_status', create_type=False), nullable=False, server_default='PENDING'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['vault_id'], ['vaults.id'], name='fk_withdrawal_requests_vault_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_withdrawal_requests_user_id'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('amount > 0', name='ck_withdrawal_requests_amount_positive'),
    )
    op.create_index(op.f('ix_withdrawal_requests_id'), 'withdrawal_requests', ['id'], unique=False)
    op.create_index(op.f('ix_withdrawal_requests_vault_id'), 'withdrawal_requests', ['vault_id'], unique=False)
    op.create_index(op.f('ix_withdrawal_requests_user_id'), 'withdrawal_requests', ['user_id'], unique=False)
    op.create_index(op.f('ix_withdrawal_requests_status'), 'withdrawal_requests', ['status'], unique=False)
    op.create_index('ix_withdrawal_requests_vault_status_created', 'withdrawal_requests', ['vault_id', 'status', 'created_at'], unique=False)
    
    # Step 8: Add vault_id column to accounts table
    op.add_column('accounts', sa.Column('vault_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_accounts_vault_id', 'accounts', 'vaults', ['vault_id'], ['id'])
    op.create_index(op.f('ix_accounts_vault_id'), 'accounts', ['vault_id'], unique=False)
    op.create_index('ix_accounts_type_vault_currency', 'accounts', ['account_type', 'vault_id', 'currency'], unique=False)


def downgrade() -> None:
    # Step 8: Remove vault_id from accounts
    op.drop_index('ix_accounts_type_vault_currency', table_name='accounts')
    op.drop_index(op.f('ix_accounts_vault_id'), table_name='accounts')
    op.drop_constraint('fk_accounts_vault_id', 'accounts', type_='foreignkey')
    op.drop_column('accounts', 'vault_id')
    
    # Step 7: Drop withdrawal_requests table
    op.drop_index('ix_withdrawal_requests_vault_status_created', table_name='withdrawal_requests')
    op.drop_index(op.f('ix_withdrawal_requests_status'), table_name='withdrawal_requests')
    op.drop_index(op.f('ix_withdrawal_requests_user_id'), table_name='withdrawal_requests')
    op.drop_index(op.f('ix_withdrawal_requests_vault_id'), table_name='withdrawal_requests')
    op.drop_index(op.f('ix_withdrawal_requests_id'), table_name='withdrawal_requests')
    op.drop_table('withdrawal_requests')
    
    # Step 6: Drop vault_accounts table
    op.drop_index('ix_vault_accounts_vault_user', table_name='vault_accounts')
    op.drop_index(op.f('ix_vault_accounts_user_id'), table_name='vault_accounts')
    op.drop_index(op.f('ix_vault_accounts_vault_id'), table_name='vault_accounts')
    op.drop_index(op.f('ix_vault_accounts_id'), table_name='vault_accounts')
    op.drop_table('vault_accounts')
    
    # Step 5: Drop vaults table
    op.drop_index(op.f('ix_vaults_status'), table_name='vaults')
    op.drop_index(op.f('ix_vaults_code'), table_name='vaults')
    op.drop_index(op.f('ix_vaults_id'), table_name='vaults')
    op.drop_table('vaults')
    
    # Step 4: Drop withdrawal_request_status enum
    op.execute("DROP TYPE IF EXISTS withdrawal_request_status")
    
    # Step 3: Drop vault_status enum
    op.execute("DROP TYPE IF EXISTS vault_status")
    
    # Note: We cannot remove enum values from operation_type and account_type enums in PostgreSQL
    # They remain in the database but are unused


