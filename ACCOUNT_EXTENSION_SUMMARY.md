# Account Extension Summary - Virtual Wallet Compartments

**Date**: 2025-12-18  
**Status**: ✅ Complete

---

## ✅ AccountType Enum Extended

**File**: `backend/app/core/accounts/models.py`

### Updated Enum Values:

```python
class AccountType(str, enum.Enum):
    # Wallet compartments (virtual wallet)
    WALLET = "WALLET"  # Legacy - backward compatibility
    WALLET_AVAILABLE = "WALLET_AVAILABLE"
    WALLET_BLOCKED = "WALLET_BLOCKED"
    WALLET_LOCKED = "WALLET_LOCKED"
    # Internal accounts
    INTERNAL_BLOCKED = "INTERNAL_BLOCKED"  # Legacy
    INTERNAL_OMNIBUS = "INTERNAL_OMNIBUS"
```

**New values added**:
- ✅ `WALLET_AVAILABLE` - Funds available for user operations
- ✅ `WALLET_BLOCKED` - Funds blocked (e.g., compliance review)
- ✅ `WALLET_LOCKED` - Funds locked (e.g., fraud detection)
- ✅ `INTERNAL_OMNIBUS` - Internal platform account

**Backward compatibility**: Existing `WALLET` and `INTERNAL_BLOCKED` values retained.

---

## ✅ Unique Constraint Added

**File**: `backend/app/core/accounts/models.py`

### Constraint Definition:

```python
__table_args__ = (
    UniqueConstraint('user_id', 'currency', 'account_type', name='uq_accounts_user_currency_type'),
)
```

**Constraint**: One account per (user_id, currency, account_type) combination.

**Effect**:
- A user can have multiple accounts per currency (different account_type)
- But only one account of each type per currency
- Example: User can have both WALLET_AVAILABLE and WALLET_BLOCKED accounts for AED, but not two WALLET_AVAILABLE accounts

---

## 📝 Documentation Added

### Code-Level Documentation (Account model):

- ✅ Wallet virtualization concept explained
- ✅ Fund availability rules per account_type documented
- ✅ Balance calculation explained (virtual wallet = sum of all accounts)
- ✅ Fund movement between compartments via LedgerEntry explained
- ✅ Constraints and immutability rules documented

### Architecture Documentation:

**File**: `docs/architecture.md`

- ✅ New section: "Wallet Virtualization via Account Types"
- ✅ Explained BLOCKED vs AVAILABLE vs LOCKED compartments
- ✅ Referenced Transaction & Operation layers
- ✅ Documented fund movement workflow

---

## 📁 Files Modified

1. ✅ `backend/app/core/accounts/models.py` - Extended enum, added constraint, added docs
2. ✅ `docs/architecture.md` - Added wallet virtualization section

---

## 🔄 Alembic Migration

### To Create Migration:

```bash
cd backend
alembic revision --autogenerate -m "Extend AccountType enum and add unique constraint on accounts"
```

**Expected output**: Migration file created in `backend/alembic/versions/` with format:
```
YYYYMMDD_HHMMSS-<revision>_extend_account_type_enum_and_add_unique_constraint_on_accounts.py
```

**Migration will**:
1. Alter PostgreSQL enum `account_type` to add new values (ALTER TYPE ... ADD VALUE)
2. Add UNIQUE constraint on (user_id, currency, account_type)

### PostgreSQL-Safe Migration Notes:

- Enum alterations: PostgreSQL requires adding values one at a time (in transaction)
- Unique constraint: Will fail if duplicate data exists - ensure data cleanup before migration
- No data loss: All existing accounts remain valid (WALLET and INTERNAL_BLOCKED retained)

### To Apply Migration:

```bash
# With Docker Compose
cd infra && docker compose exec backend alembic upgrade head

# Or with Makefile
make migrate

# Or directly
cd backend && alembic upgrade head
```

---

## 📊 Account Compartments Summary

| Account Type | Purpose | Availability |
|-------------|---------|--------------|
| `WALLET_AVAILABLE` | User-accessible funds | Available for operations |
| `WALLET_BLOCKED` | Compliance/regulatory holds | Blocked until review |
| `WALLET_LOCKED` | Security/fraud holds | Locked until admin action |
| `INTERNAL_OMNIBUS` | Platform operations | Internal use only |
| `WALLET` (legacy) | Backward compatibility | Treated as AVAILABLE |
| `INTERNAL_BLOCKED` (legacy) | Legacy internal | Deprecated |

---

## ✅ Validation Checklist

- [x] AccountType enum extended with new compartments
- [x] Backward compatibility maintained (WALLET, INTERNAL_BLOCKED retained)
- [x] Unique constraint added on (user_id, currency, account_type)
- [x] Code-level documentation added (virtualization explained)
- [x] Architecture docs updated with wallet virtualization section
- [x] Default account_type changed to WALLET_AVAILABLE
- [x] Model syntax validated
- [x] Ready for migration generation

---

**Status**: ✅ Account extension complete - Ready for migration generation and testing.


