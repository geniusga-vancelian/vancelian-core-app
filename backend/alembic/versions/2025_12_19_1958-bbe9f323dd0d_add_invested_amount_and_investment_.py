"""add_invested_amount_and_investment_intents_v1_1

Revision ID: bbe9f323dd0d
Revises: 6d2c3d34d376
Create Date: 2025-12-19 19:58:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'bbe9f323dd0d'
down_revision = '6d2c3d34d376'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create investment_intent_status enum
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'investment_intent_status') THEN
                CREATE TYPE investment_intent_status AS ENUM ('PENDING', 'CONFIRMED', 'REJECTED');
            END IF;
        END $$;
    """)
    
    # Add invested_amount column to offers table
    op.add_column('offers', sa.Column('invested_amount', sa.Numeric(24, 8), nullable=False, server_default='0'))
    
    # Sync invested_amount with committed_amount for existing data
    op.execute("UPDATE offers SET invested_amount = committed_amount WHERE invested_amount = 0")
    
    # Add check constraint for invested_amount
    op.create_check_constraint(
        'check_invested_amount_non_negative',
        'offers',
        'invested_amount >= 0'
    )
    op.create_check_constraint(
        'check_invested_not_exceed_max',
        'offers',
        'invested_amount <= max_amount'
    )
    
    # Create investment_intents table
    op.create_table(
        'investment_intents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('offer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('requested_amount', sa.Numeric(24, 8), nullable=False),
        sa.Column('allocated_amount', sa.Numeric(24, 8), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='AED'),
        sa.Column('status', postgresql.ENUM('PENDING', 'CONFIRMED', 'REJECTED', name='investment_intent_status', create_type=False), nullable=False, server_default='PENDING'),
        sa.Column('idempotency_key', sa.String(255), nullable=True),
        sa.Column('operation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['offer_id'], ['offers.id'], name='fk_investment_intents_offer_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_investment_intents_user_id'),
        sa.ForeignKeyConstraint(['operation_id'], ['operations.id'], name='fk_investment_intents_operation_id'),
        sa.PrimaryKeyConstraint('id', name='pk_investment_intents')
    )
    
    # Create indexes
    op.create_index('ix_investment_intents_offer_id', 'investment_intents', ['offer_id'])
    op.create_index('ix_investment_intents_user_id', 'investment_intents', ['user_id'])
    op.create_index('ix_investment_intents_status', 'investment_intents', ['status'])
    op.create_index('ix_investment_intents_idempotency_key', 'investment_intents', ['idempotency_key'], unique=True)
    op.create_index('ix_investment_intents_operation_id', 'investment_intents', ['operation_id'])
    op.create_index('idx_investment_intents_offer_user', 'investment_intents', ['offer_id', 'user_id'])
    op.create_index('idx_investment_intents_offer_status', 'investment_intents', ['offer_id', 'status'])
    op.create_index('idx_investment_intents_user_status', 'investment_intents', ['user_id', 'status'])
    
    # Create check constraints
    op.create_check_constraint(
        'check_intent_requested_amount_positive',
        'investment_intents',
        'requested_amount > 0'
    )
    op.create_check_constraint(
        'check_intent_allocated_amount_non_negative',
        'investment_intents',
        'allocated_amount >= 0'
    )
    op.create_check_constraint(
        'check_intent_allocated_not_exceed_requested',
        'investment_intents',
        'allocated_amount <= requested_amount'
    )


def downgrade() -> None:
    # Drop investment_intents table
    op.drop_table('investment_intents')
    
    # Drop invested_amount column
    op.drop_constraint('check_invested_not_exceed_max', 'offers', type_='check')
    op.drop_constraint('check_invested_amount_non_negative', 'offers', type_='check')
    op.drop_column('offers', 'invested_amount')
    
    # Drop enum (only if no other tables use it)
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE udt_name = 'investment_intent_status'
            ) THEN
                DROP TYPE IF EXISTS investment_intent_status;
            END IF;
        END $$;
    """)
