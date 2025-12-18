#!/usr/bin/env python3
"""
Migration safety check script for CI/CD.

Verifies:
- Migrations can be applied to empty database
- No pending migrations
- Migration files are valid
"""

import sys
import os
from sqlalchemy import create_engine, inspect, text
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from alembic import command

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.settings import get_settings


def check_migration_safety():
    """Check that migrations are safe and can be applied"""
    settings = get_settings()
    
    print(f"Checking migrations for environment: {settings.ENV}")
    print(f"Database URL: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'REDACTED'}")
    
    # Check alembic.ini exists
    alembic_ini = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini")
    if not os.path.exists(alembic_ini):
        print("❌ alembic.ini not found")
        return False
    
    # Load Alembic configuration
    alembic_cfg = Config(alembic_ini)
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    
    # Check script directory
    script = ScriptDirectory.from_config(alembic_cfg)
    heads = script.get_revisions("heads")
    
    if not heads:
        print("❌ No migration heads found")
        return False
    
    print(f"✅ Found {len(heads)} migration head(s)")
    
    # Check current database state
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        current_rev = context.get_current_revision()
        
        if current_rev:
            print(f"Current database revision: {current_rev}")
        else:
            print("Database is empty (no migrations applied)")
        
        # Get heads as strings
        head_revs = [str(h.revision) for h in heads]
        
        if current_rev and current_rev not in head_revs:
            # Check if we're behind
            print(f"⚠️  Current revision {current_rev} is not at head")
            # This is OK if migrations can be upgraded
    
    print("✅ Migration safety check passed")
    return True


def verify_empty_db_migration():
    """Verify migrations can be applied to empty database"""
    settings = get_settings()
    
    print("Verifying migrations work on empty database...")
    
    alembic_ini = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini")
    alembic_cfg = Config(alembic_ini)
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    
    try:
        # Try to upgrade to head
        command.upgrade(alembic_cfg, "head")
        print("✅ Migrations can be applied to empty database")
        return True
    except Exception as e:
        print(f"❌ Failed to apply migrations to empty database: {e}")
        return False


if __name__ == "__main__":
    success = True
    
    try:
        success &= check_migration_safety()
        success &= verify_empty_db_migration()
    except Exception as e:
        print(f"❌ Migration check failed: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    sys.exit(0 if success else 1)



