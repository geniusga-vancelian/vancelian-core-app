"""
Alembic environment configuration
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys
from dotenv import load_dotenv

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

load_dotenv()

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import Base and models (all models must be imported for Alembic to detect them)
# Use models registry to avoid circular imports
from app.infrastructure.database import Base

# Import all models through registry to ensure Alembic detects them
# Note: Import from models registry which includes all models
import app.models  # This imports all models registered in app/models/__init__.py
from app.models import (
    User,
    Account,
    Transaction,
    Operation,
    LedgerEntry,
    AuditLog,
    Offer,
    OfferInvestment,
    WalletLock,
)
# Import vault models directly (they may not be in __all__)
from app.core.vaults.models import Vault, VaultAccount, WithdrawalRequest, VestingLot, VestingLotStatus

target_metadata = Base.metadata


def get_url():
    """Get database URL from environment"""
    return os.getenv("DATABASE_URL", "postgresql://vancelian:vancelian_password@postgres:5432/vancelian_core")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

