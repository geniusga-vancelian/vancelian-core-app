"""add_system_wallets_offer_id_and_extend_account_types

Revision ID: add_system_wallets_20250126
Revises: create_vaults_20251225
Create Date: 2025-01-26 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_system_wallets_20250126'
down_revision = 'create_vaults_20251225'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Add new enum values to account_type enum
    op.execute("""
        DO $$ 
        BEGIN
            -- Add VAULT_POOL_LOCKED if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'VAULT_POOL_LOCKED' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'account_type')
            ) THEN
                ALTER TYPE account_type ADD VALUE 'VAULT_POOL_LOCKED';
            END IF;
            
            -- Add VAULT_POOL_BLOCKED if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'VAULT_POOL_BLOCKED' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'account_type')
            ) THEN
                ALTER TYPE account_type ADD VALUE 'VAULT_POOL_BLOCKED';
            END IF;
            
            -- Add OFFER_POOL_AVAILABLE if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'OFFER_POOL_AVAILABLE' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'account_type')
            ) THEN
                ALTER TYPE account_type ADD VALUE 'OFFER_POOL_AVAILABLE';
            END IF;
            
            -- Add OFFER_POOL_LOCKED if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'OFFER_POOL_LOCKED' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'account_type')
            ) THEN
                ALTER TYPE account_type ADD VALUE 'OFFER_POOL_LOCKED';
            END IF;
            
            -- Add OFFER_POOL_BLOCKED if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'OFFER_POOL_BLOCKED' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'account_type')
            ) THEN
                ALTER TYPE account_type ADD VALUE 'OFFER_POOL_BLOCKED';
            END IF;
        END $$;
    """)
    
    # Step 2: Add offer_id column to accounts table
    op.add_column('accounts', sa.Column('offer_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_accounts_offer_id', 'accounts', 'offers', ['offer_id'], ['id'])
    op.create_index(op.f('ix_accounts_offer_id'), 'accounts', ['offer_id'], unique=False)
    
    # Step 3: Create composite index for offer pool accounts
    op.create_index('ix_accounts_type_offer_currency', 'accounts', ['account_type', 'offer_id', 'currency'], unique=False)
    
    # Step 4: Add unique constraint to prevent duplicate accounts
    # Note: In PostgreSQL, NULL != NULL, so this constraint allows multiple rows with NULL values.
    # We rely on application-level "get or create" logic to prevent duplicates.
    op.create_unique_constraint('uq_accounts_unique', 'accounts', ['account_type', 'user_id', 'vault_id', 'offer_id', 'currency'])


def downgrade() -> None:
    # Step 4: Drop unique constraint
    op.drop_constraint('uq_accounts_unique', 'accounts', type_='unique')
    
    # Step 3: Drop composite index for offer pool accounts
    op.drop_index('ix_accounts_type_offer_currency', table_name='accounts')
    
    # Step 2: Remove offer_id from accounts
    op.drop_index(op.f('ix_accounts_offer_id'), table_name='accounts')
    op.drop_constraint('fk_accounts_offer_id', 'accounts', type_='foreignkey')
    op.drop_column('accounts', 'offer_id')
    
    # Step 1: Note: We cannot remove enum values from account_type enum in PostgreSQL
    # They remain in the database but are unused after downgrade
    # This is a known limitation of PostgreSQL enums


