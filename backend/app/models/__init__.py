"""
Models registry for Alembic - Import all models here to ensure Base.metadata is complete

This module is used ONLY by Alembic to discover all models.
Import order matters to avoid circular dependencies:
1. Base and common models first
2. Models without foreign keys
3. Models with foreign keys (in dependency order)
"""

# Import Base first
from app.infrastructure.database import Base

# Import models in dependency order to avoid circular imports
# 1. Security models (no dependencies)
from app.core.security.models import Role

# 2. User model (no foreign keys to other domain models)
from app.core.users.models import User, UserStatus

# 3. Account model (depends on User)
from app.core.accounts.models import Account, AccountType

# 4. Transaction model (depends on User)
from app.core.transactions.models import Transaction, TransactionType, TransactionStatus

# 5. Operation model (depends on Transaction)
from app.core.ledger.models import Operation, OperationType, OperationStatus, LedgerEntry, LedgerEntryType

# 6. AuditLog model (depends on User and Role)
from app.core.compliance.models import AuditLog

# 7. Offer models (depends on User and Operation)
from app.core.offers.models import (
    Offer, OfferInvestment, OfferStatus, OfferInvestmentStatus,
    InvestmentIntent, InvestmentIntentStatus,
    OfferMedia, MediaType, MediaVisibility,
    OfferDocument, DocumentKind, DocumentVisibility,
)

# Export all for convenience
__all__ = [
    "Base",
    "User",
    "UserStatus",
    "Account",
    "AccountType",
    "Transaction",
    "TransactionType",
    "TransactionStatus",
    "Operation",
    "OperationType",
    "OperationStatus",
    "LedgerEntry",
    "LedgerEntryType",
    "AuditLog",
    "Role",
    "Offer",
    "OfferInvestment",
    "OfferStatus",
    "OfferInvestmentStatus",
    "InvestmentIntent",
    "InvestmentIntentStatus",
    "OfferMedia",
    "MediaType",
    "MediaVisibility",
    "OfferDocument",
    "DocumentKind",
    "DocumentVisibility",
]

