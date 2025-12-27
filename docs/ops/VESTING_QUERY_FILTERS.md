# Vesting Query Filters - Checklist

**Date:** 2025-01-27  
**Purpose:** Document exact filters used to select mature vesting lots for release

---

## Query Location

**File:** `backend/app/services/vesting_service.py`  
**Function:** `release_avenir_vesting_lots()`  
**Lines:** 131-142

---

## Exact WHERE Conditions

```python
mature_lots = db.query(VestingLot).filter(
    and_(
        VestingLot.vault_code == 'AVENIR',           # Exact string match
        VestingLot.release_day <= as_of_date,        # DATE comparison (<=)
        VestingLot.status == VestingLotStatus.VESTED.value,  # Status must be 'VESTED'
        VestingLot.released_amount < VestingLot.amount,      # Not fully released
        VestingLot.currency == currency,              # Exact currency match (e.g., 'AED')
    )
).order_by(
    VestingLot.release_day.asc(),
    VestingLot.created_at.asc(),
).limit(max_lots).with_for_update(skip_locked=True).all()
```

---

## Checklist: A Lot Must Have These Fields to Be Selected

### Required Fields

1. **`vault_code`** = `'AVENIR'` (exact string, case-sensitive)
2. **`release_day`** <= `as_of_date` (DATE type, comparison is `<=`)
3. **`status`** = `VestingLotStatus.VESTED.value` (exact value, typically `'VESTED'`)
4. **`released_amount`** < `amount` (not fully released)
5. **`currency`** = `currency` parameter (exact match, e.g., `'AED'`)

### Additional Checks (After Query)

The service also performs these checks in the loop (lines 149-174):

6. **Idempotence check:** `lot.status == VestingLotStatus.RELEASED.value` → skip
7. **Idempotence check:** `lot.released_amount >= lot.amount` → skip
8. **Double-check maturity:** `lot.release_day > as_of_date` → skip
9. **Double-check status:** `lot.status != VestingLotStatus.VESTED.value` → skip
10. **Release amount:** `release_amount <= 0` → skip

---

## Date Handling

### `as_of_date` Normalization

**Function:** `normalize_to_utc_midnight(d: date) -> date`  
**Location:** `backend/app/services/vesting_service.py:59-66`

```python
def normalize_to_utc_midnight(d: date) -> date:
    """
    Normalize a date to UTC midnight (already a date, return as-is).
    
    Note: This function is a no-op since date objects don't have timezone info.
    The timezone is implicit (UTC) in our system.
    """
    return d
```

**Behavior:** No-op for `date` objects. The function just returns the date as-is.

### `release_day` Type

**Model:** `VestingLot.release_day` is `Column(Date, nullable=False)`  
**Type:** Python `date` object (no timezone, UTC implicit)

### Comparison

- `release_day <= as_of_date` is a direct DATE comparison
- Both must be `date` objects (not `datetime`)
- No timezone conversion needed

---

## Test Fixture Requirements

To create a lot that will be selected by the query:

```python
vesting_lot = VestingLot(
    vault_id=avenir_vault.id,                    # FK to vaults table
    vault_code='AVENIR',                          # Exact string match
    user_id=user_id,                              # FK to users table
    currency='AED',                               # Exact currency match
    deposit_day=date.today() - timedelta(days=366),  # DATE type
    release_day=date.today() - timedelta(days=1),    # Must be <= as_of_date (DATE type)
    amount=Decimal('10000.00'),                   # > 0
    released_amount=Decimal('0.00'),              # Must be < amount
    status=VestingLotStatus.VESTED.value,         # Must be 'VESTED'
    source_operation_id=operation_deposit.id,     # FK to operations table
)
```

**Critical Points:**
- `release_day` must be a `date` object (not `datetime`)
- `release_day` must be `<= as_of_date` (typically `date.today()`)
- `status` must be exactly `VestingLotStatus.VESTED.value` (check enum value)
- `released_amount` must be `< amount` (not `<=`)

---

## Transaction Visibility

**Important:** After creating a lot, ensure it's visible in the query:

1. **Commit the transaction:**
   ```python
   db_session.add(vesting_lot)
   db_session.commit()
   ```

2. **Refresh to ensure visibility:**
   ```python
   db_session.refresh(vesting_lot)
   ```

3. **Or expire all to simulate new transaction:**
   ```python
   db_session.expire_all()
   ```

**Note:** `with_for_update(skip_locked=True)` may skip rows locked by other transactions, but in tests this shouldn't be an issue.

---

## Wallet Lock Requirements (For Fallback Search)

If the service uses fallback search for wallet_locks (when `operation_id` link is missing), the lock must match:

```python
WalletLock.user_id == lot.user_id
WalletLock.currency == currency
WalletLock.reason == LockReason.VAULT_AVENIR_VESTING.value
WalletLock.reference_type == 'VAULT'
WalletLock.reference_id == lot.vault_id
WalletLock.status == LockStatus.ACTIVE.value
func.abs(WalletLock.amount - lot.amount) <= Decimal('0.01')  # Amount match (tolerance)
func.date(WalletLock.created_at) == lot.deposit_day           # Same UTC day
```

---

## Common Issues in Tests

1. **Wrong status:** Using `'LOCKED'` or `'ACTIVE'` instead of `'VESTED'`
2. **Wrong date type:** Using `datetime` instead of `date` for `release_day`
3. **Future release_day:** `release_day > as_of_date` (lot not mature)
4. **Fully released:** `released_amount >= amount` (already released)
5. **Transaction visibility:** Lot not committed/refreshed before query
6. **Wrong currency:** Currency mismatch (e.g., `'USD'` vs `'AED'`)
7. **Wrong vault_code:** Using `'avenir'` (lowercase) instead of `'AVENIR'`

---

**Dernière mise à jour:** 2025-01-27

