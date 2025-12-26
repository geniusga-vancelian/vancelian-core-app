"""
Seed script to create FLEX and AVENIR vaults (idempotent)
"""

import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Import all models first to ensure relationships are resolved
from app.models import *  # This ensures all models are loaded

from sqlalchemy.orm import Session
from app.infrastructure.database import get_db, engine
from app.core.vaults.models import Vault, VaultStatus
from app.services.vault_helpers import get_or_create_vault_pool_cash_account


def seed_vaults(db: Session):
    """Create FLEX and AVENIR vaults if they don't exist"""
    print("Seeding vaults...")
    
    # FLEX vault
    flex_vault = db.query(Vault).filter(Vault.code == "FLEX").first()
    if not flex_vault:
        flex_vault = Vault(
            code="FLEX",
            name="FLEX - Flexible Vault",
            status=VaultStatus.ACTIVE,
            cash_balance=0,
            total_aum=0,
            locked_until=None,
        )
        db.add(flex_vault)
        db.flush()
        print("  ✓ Created FLEX vault")
    else:
        print("  ✓ FLEX vault already exists")
    
    # AVENIR vault
    avenir_vault = db.query(Vault).filter(Vault.code == "AVENIR").first()
    if not avenir_vault:
        avenir_vault = Vault(
            code="AVENIR",
            name="AVENIR - Future Vault",
            status=VaultStatus.ACTIVE,
            cash_balance=0,
            total_aum=0,
            locked_until=None,  # Will be set on first deposit
        )
        db.add(avenir_vault)
        db.flush()
        print("  ✓ Created AVENIR vault")
    else:
        print("  ✓ AVENIR vault already exists")
    
    # Ensure vault pool cash accounts exist for each vault
    currency = "AED"  # Default currency
    get_or_create_vault_pool_cash_account(db, flex_vault.id, currency)
    print(f"  ✓ Ensured VAULT_POOL_CASH account for FLEX ({currency})")
    get_or_create_vault_pool_cash_account(db, avenir_vault.id, currency)
    print(f"  ✓ Ensured VAULT_POOL_CASH account for AVENIR ({currency})")
    
    db.commit()
    print("Vaults seeding complete.")


if __name__ == "__main__":
    # Create a new database session
    with next(get_db()) as db:
        seed_vaults(db)
