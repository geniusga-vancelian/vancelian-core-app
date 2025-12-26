"""merge_system_wallets_and_wallet_locks

Revision ID: 7e6c633bb443
Revises: add_system_wallets_20250126, create_wallet_locks_20250126
Create Date: 2025-12-26 06:24:21.484871

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7e6c633bb443'
down_revision = ('add_system_wallets_20250126', 'create_wallet_locks_20250126')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass



