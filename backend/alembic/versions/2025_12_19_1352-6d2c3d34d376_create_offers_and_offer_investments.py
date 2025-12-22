"""create_offers_and_offer_investments

Revision ID: 6d2c3d34d376
Revises: 96e12468c78b
Create Date: 2025-12-19 13:52:48.762667

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '6d2c3d34d376'
down_revision = '96e12468c78b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old investment tables if they exist (from previous implementation)
    op.execute("DROP TABLE IF EXISTS investment_intents CASCADE")
    op.execute("DROP TABLE IF EXISTS investment_offers CASCADE")
    
    # Migrate offer_status enum if it exists with old values
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'offer_status') THEN
                -- Check if enum has OPEN value (old system)
                IF EXISTS (
                    SELECT 1 FROM pg_enum 
                    WHERE enumlabel = 'OPEN' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'offer_status')
                ) THEN
                    -- Drop old enum and create new one
                    DROP TYPE IF EXISTS offer_status CASCADE;
                    CREATE TYPE offer_status AS ENUM ('DRAFT', 'LIVE', 'PAUSED', 'CLOSED');
                END IF;
            ELSE
                -- Create new enum
                CREATE TYPE offer_status AS ENUM ('DRAFT', 'LIVE', 'PAUSED', 'CLOSED');
            END IF;
        END $$;
    """)
    
    # Create offer_investment_status enum
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'offer_investment_status') THEN
                CREATE TYPE offer_investment_status AS ENUM ('PENDING', 'ACCEPTED', 'REJECTED');
            END IF;
        END $$;
    """)
    
    # Create offers table
    op.create_table('offers',
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('max_amount', sa.Numeric(precision=24, scale=8), nullable=False),
    sa.Column('committed_amount', sa.Numeric(precision=24, scale=8), nullable=False, server_default='0'),
    sa.Column('maturity_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', postgresql.ENUM('DRAFT', 'LIVE', 'PAUSED', 'CLOSED', name='offer_status', create_type=False), nullable=False, server_default='DRAFT'),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('committed_amount <= max_amount', name='check_committed_not_exceed_max'),
    sa.CheckConstraint('committed_amount >= 0', name='check_committed_amount_non_negative'),
    sa.CheckConstraint('max_amount > 0', name='check_max_amount_positive'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_offer_status_currency', 'offers', ['status', 'currency'], unique=False)
    op.create_index(op.f('ix_offers_code'), 'offers', ['code'], unique=True)
    op.create_index(op.f('ix_offers_currency'), 'offers', ['currency'], unique=False)
    op.create_index(op.f('ix_offers_id'), 'offers', ['id'], unique=False)
    op.create_index(op.f('ix_offers_status'), 'offers', ['status'], unique=False)
    
    # Create offer_investments table
    op.create_table('offer_investments',
    sa.Column('offer_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('requested_amount', sa.Numeric(precision=24, scale=8), nullable=False),
    sa.Column('accepted_amount', sa.Numeric(precision=24, scale=8), nullable=False, server_default='0'),
    sa.Column('currency', sa.String(length=3), nullable=False, server_default='AED'),
    sa.Column('status', postgresql.ENUM('PENDING', 'ACCEPTED', 'REJECTED', name='offer_investment_status', create_type=False), nullable=False, server_default='PENDING'),
    sa.Column('idempotency_key', sa.String(length=255), nullable=True),
    sa.Column('operation_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('accepted_amount <= requested_amount', name='check_accepted_not_exceed_requested'),
    sa.CheckConstraint('accepted_amount >= 0', name='check_accepted_amount_non_negative'),
    sa.CheckConstraint('requested_amount > 0', name='check_requested_amount_positive'),
    sa.ForeignKeyConstraint(['offer_id'], ['offers.id'], name='fk_offer_investments_offer_id'),
    sa.ForeignKeyConstraint(['operation_id'], ['operations.id'], name='fk_offer_investments_operation_id'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_offer_investments_user_id'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_offer_investments_offer_status', 'offer_investments', ['offer_id', 'status'], unique=False)
    op.create_index('idx_offer_investments_offer_user', 'offer_investments', ['offer_id', 'user_id'], unique=False)
    op.create_index('idx_offer_investments_user_status', 'offer_investments', ['user_id', 'status'], unique=False)
    op.create_index(op.f('ix_offer_investments_id'), 'offer_investments', ['id'], unique=False)
    op.create_index(op.f('ix_offer_investments_idempotency_key'), 'offer_investments', ['idempotency_key'], unique=True)
    op.create_index(op.f('ix_offer_investments_offer_id'), 'offer_investments', ['offer_id'], unique=False)
    op.create_index(op.f('ix_offer_investments_operation_id'), 'offer_investments', ['operation_id'], unique=False)
    op.create_index(op.f('ix_offer_investments_status'), 'offer_investments', ['status'], unique=False)
    op.create_index(op.f('ix_offer_investments_user_id'), 'offer_investments', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop new tables
    op.drop_index(op.f('ix_offer_investments_user_id'), table_name='offer_investments')
    op.drop_index(op.f('ix_offer_investments_status'), table_name='offer_investments')
    op.drop_index(op.f('ix_offer_investments_operation_id'), table_name='offer_investments')
    op.drop_index(op.f('ix_offer_investments_offer_id'), table_name='offer_investments')
    op.drop_index(op.f('ix_offer_investments_idempotency_key'), table_name='offer_investments')
    op.drop_index(op.f('ix_offer_investments_id'), table_name='offer_investments')
    op.drop_index('idx_offer_investments_user_status', table_name='offer_investments')
    op.drop_index('idx_offer_investments_offer_user', table_name='offer_investments')
    op.drop_index('idx_offer_investments_offer_status', table_name='offer_investments')
    op.drop_table('offer_investments')
    op.drop_index(op.f('ix_offers_status'), table_name='offers')
    op.drop_index(op.f('ix_offers_id'), table_name='offers')
    op.drop_index(op.f('ix_offers_currency'), table_name='offers')
    op.drop_index(op.f('ix_offers_code'), table_name='offers')
    op.drop_index('idx_offer_status_currency', table_name='offers')
    op.drop_table('offers')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS offer_investment_status")
    op.execute("DROP TYPE IF EXISTS offer_status")
