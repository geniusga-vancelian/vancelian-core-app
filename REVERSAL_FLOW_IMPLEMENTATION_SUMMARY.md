# Deposit Rejection/Reversal Flow Implementation Summary

**Date**: 2025-12-18  
**Status**: ✅ Complete

---

## ✅ OperationType Extension

**Added**: `REVERSAL_DEPOSIT` to `OperationType` enum

**File**: `backend/app/core/ledger/models.py`

```python
class OperationType(str, enum.Enum):
    DEPOSIT_AED = "DEPOSIT_AED"
    INVEST_EXCLUSIVE = "INVEST_EXCLUSIVE"
    RELEASE_FUNDS = "RELEASE_FUNDS"
    REVERSAL_DEPOSIT = "REVERSAL_DEPOSIT"  # Reversal of deposit (rejection)
    ADJUSTMENT = "ADJUSTMENT"
    REVERSAL = "REVERSAL"  # Generic reversal
```

---

## ✅ TransactionStatus Rules (Deposit Rejection)

**Transaction Status Engine Extended**:

For `TransactionType = DEPOSIT`:
- **FAILED** → When `REVERSAL_DEPOSIT` operation is COMPLETED
- **FAILED** → When any Operation FAILED
- **AVAILABLE** → When `RELEASE_FUNDS` completed (only if not already FAILED)
- Once FAILED, transaction cannot become AVAILABLE

**Implementation**:
- Updated `_compute_deposit_status()` in `transaction_engine.py`
- Checks for `REVERSAL_DEPOSIT` completion first (highest priority)
- Returns `TransactionStatus.FAILED` when reversal is completed

---

## ✅ Service: reject_deposit

**Function**:
```python
def reject_deposit(
    *,
    db: Session,
    transaction_id: UUID,
    user_id: UUID,
    currency: str,
    amount: Decimal,
    reason: str,
    actor_user_id: Optional[UUID] = None,
) -> Operation
```

**Behavior**:
1. Validates amount > 0
2. Validates reason is provided (mandatory)
3. Validates sufficient balance in WALLET_BLOCKED
4. Creates Operation:
   - `type` = REVERSAL_DEPOSIT
   - `status` = COMPLETED
5. Creates LedgerEntries (double-entry reversal):
   - DEBIT WALLET_BLOCKED (remove funds from user)
   - CREDIT INTERNAL_OMNIBUS (return funds to internal account)
6. Creates AuditLog:
   - `action` = "DEPOSIT_REJECTED"
   - `actor_role` = COMPLIANCE
   - `reason` = Required

**Ledger Immutability**:
- No entries deleted or modified
- New reversal entries created that offset original deposit
- Original deposit entries remain in ledger (audit trail intact)

---

## ✅ Endpoint Created

**Route**: `POST /admin/v1/compliance/reject-deposit`

**Access**: COMPLIANCE or OPS role only (RBAC enforced).

**Request Body**:
```json
{
  "transaction_id": "uuid",
  "reason": "Sanctions match / invalid IBAN"
}
```

**Response** (200 OK):
```json
{
  "transaction_id": "uuid",
  "status": "FAILED"
}
```

---

## ✅ Business Flow

**On Request**:
1. Validates transaction exists
2. Validates transaction.type == DEPOSIT
3. Validates transaction.status == COMPLIANCE_REVIEW
4. Computes amount from original DEPOSIT_AED operation
5. Calls `reject_deposit()` service:
   - Creates Operation (REVERSAL_DEPOSIT, COMPLETED)
   - Creates LedgerEntries: DEBIT WALLET_BLOCKED, CREDIT INTERNAL_OMNIBUS
   - Creates AuditLog (DEPOSIT_REJECTED, COMPLIANCE role)
6. Triggers `recompute_transaction_status()`:
   - Status updates: COMPLIANCE_REVIEW → **FAILED**
7. Returns response with transaction_id and status

---

## ✅ Funds Movement

**Confirmed**: Funds moved from BLOCKED → INTERNAL_OMNIBUS only

**Service Call**:
```python
reject_deposit(
    transaction_id,
    user_id,
    currency,
    amount,  # Computed from original deposit
    reason,  # Mandatory
    actor_user_id,
)
```

**LedgerEntries Created**:
- DEBIT WALLET_BLOCKED account (amount = -amount)
- CREDIT INTERNAL_OMNIBUS account (amount = +amount)

**Result**: Funds returned to INTERNAL_OMNIBUS, transaction status = FAILED.

---

## ✅ Transaction Status

**Final Status**: FAILED

**Transaction Status Engine**:
- Detects REVERSAL_DEPOSIT operation completion
- Updates transaction status to FAILED
- Status remains FAILED (cannot become AVAILABLE after rejection)

---

## ✅ Audit Logging

**AuditLog Created**:
- `action` = "DEPOSIT_REJECTED"
- `actor_role` = COMPLIANCE
- `entity_type` = "Operation"
- `entity_id` = operation.id
- `before` = blocked balance before rejection
- `after` = blocked balance after rejection
- `reason` = **Mandatory** (from request)

---

## ✅ Error Handling

**HTTP Status Codes**:
- `200 OK` - Success
- `403 Forbidden` - Role not allowed (RBAC)
- `404 Not Found` - Transaction not found
- `409 Conflict` - Transaction in wrong state (not COMPLIANCE_REVIEW)
- `422 Unprocessable Entity` - Validation errors
- `500 Internal Server Error` - Unexpected errors

---

## 📁 Files Created

None (extended existing files)

---

## 📁 Files Modified

1. ✅ `backend/app/core/ledger/models.py` - Added REVERSAL_DEPOSIT to OperationType
2. ✅ `backend/app/services/transaction_engine.py` - Extended DEPOSIT status rules (REVERSAL → FAILED)
3. ✅ `backend/app/services/fund_services.py` - Added reject_deposit() service function
4. ✅ `backend/app/services/__init__.py` - Exported reject_deposit
5. ✅ `backend/app/schemas/compliance.py` - Added RejectDepositRequest and RejectDepositResponse
6. ✅ `backend/app/api/admin/compliance.py` - Added reject-deposit endpoint
7. ✅ `docs/api.md` - Added Deposit Rejection section

---

## ✅ Verification

- ✅ REVERSAL_DEPOSIT OperationType added
- ✅ Transaction Status Engine extended (REVERSAL → FAILED)
- ✅ RBAC enforced (COMPLIANCE, OPS only)
- ✅ Validations implemented (transaction state, reason mandatory)
- ✅ Audit logging with mandatory reason
- ✅ Funds moved BLOCKED → INTERNAL_OMNIBUS only (confirmed)
- ✅ Transaction ends in FAILED status (confirmed)
- ✅ Ledger immutability preserved (new entries created, no deletions)
- ✅ Error handling with proper HTTP codes

---

**Status**: ✅ Deposit rejection/reversal flow complete - Ready for compliance team use.


