# ZAND WEBHOOK ACCOUNTING — VÉRIFICATION

Ce document confirme la comptabilisation des dépôts Zand via webhook.

## VÉRIFICATION COMPLÈTE

### ✅ 1. Deposit Webhook — Account Crédité

**Fichier**: `backend/app/api/webhooks/zand.py` (ligne 26-90)

**Route**: `POST /webhooks/zand/deposit`

**Fonction appelée**: `record_deposit_blocked()` (ligne 68)

**Account crédité**: ✅ **WALLET_BLOCKED** (pas WALLET_LOCKED)

**Code confirmé**:
```python
# backend/app/services/fund_services.py:64
blocked_account_id = wallet_accounts[AccountType.WALLET_BLOCKED.value]

# Ligne 102-108: CREDIT WALLET_BLOCKED
credit_entry = LedgerEntry(
    operation_id=operation.id,
    account_id=blocked_account_id,  # WALLET_BLOCKED
    amount=amount,
    currency=currency,
    entry_type=LedgerEntryType.CREDIT,
)
```

### ✅ 2. Operation Type

**Type**: ✅ **DEPOSIT_AED** (pas DEPOSIT_FIAT)

**Code confirmé**:
```python
# backend/app/services/fund_services.py:87-96
operation = Operation(
    transaction_id=transaction_id,
    type=OperationType.DEPOSIT_AED,  # ✅ DEPOSIT_AED
    status=OperationStatus.COMPLETED,
    idempotency_key=idempotency_key,
    metadata={
        'provider_reference': provider_reference,
        'currency': currency,
    },
)
```

### ✅ 3. Pas de Lock Utilisateur

**Confirmé**: ✅ Aucune logique de lock utilisateur appliquée

- Les fonds vont directement dans **WALLET_BLOCKED**
- Aucun appel à `lock_funds_for_investment()`
- Aucun mouvement vers WALLET_LOCKED

### 4. Ledger Debit/Credit Accounts

**Double-entry**:

| Account Type | User ID | Currency | Amount | Entry Type | Direction |
|--------------|---------|----------|--------|------------|-----------|
| WALLET_BLOCKED | user_id | AED | +amount | CREDIT | ✅ Crédité |
| INTERNAL_OMNIBUS | NULL (system) | AED | -amount | DEBIT | Débité |

**Code confirmé**:
```python
# CREDIT user's WALLET_BLOCKED
credit_entry = LedgerEntry(
    operation_id=operation.id,
    account_id=blocked_account_id,  # WALLET_BLOCKED (user_id, currency)
    amount=amount,  # Positif
    currency=currency,
    entry_type=LedgerEntryType.CREDIT,
)

# DEBIT INTERNAL_OMNIBUS
debit_entry = LedgerEntry(
    operation_id=operation.id,
    account_id=omnibus_account_id,  # INTERNAL_OMNIBUS (user_id=NULL)
    amount=-amount,  # Négatif
    currency=currency,
    entry_type=LedgerEntryType.DEBIT,
)
```

**Vérification double-entry**: CREDIT(+amount) + DEBIT(-amount) = 0 ✅

### 5. Wallet Balances Impactés

**Compartiment impacté**: ✅ **blocked_balance** uniquement

| Balance | Avant | Opération | Après |
|---------|-------|-----------|-------|
| `blocked_balance` | X | +amount | X + amount |
| `available_balance` | Y | (aucun changement) | Y |
| `locked_balance` | Z | (aucun changement) | Z |
| `total_balance` | X+Y+Z | +amount | X+Y+Z + amount |

**Impact sur GET /api/v1/wallet**:
- `blocked_balance` → augmente
- `available_balance` → inchangé
- `locked_balance` → inchangé
- `total_balance` → augmente

### ✅ 6. Compliance Release — BLOCKED → AVAILABLE

**Fichier**: `backend/app/services/fund_services.py` (ligne 160-270)

**Fonction**: `release_compliance_funds()`

**Endpoint Admin**: `POST /admin/v1/compliance/release` (`backend/app/api/admin/compliance.py:94`)

**Flow confirmé**: ✅ **WALLET_BLOCKED → WALLET_AVAILABLE**

**Code confirmé**:
```python
# Ligne 185-187: Get accounts
blocked_account_id = wallet_accounts[AccountType.WALLET_BLOCKED.value]
available_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]

# Ligne 212-218: DEBIT WALLET_BLOCKED
debit_entry = LedgerEntry(
    operation_id=operation.id,
    account_id=blocked_account_id,  # WALLET_BLOCKED
    amount=-amount,  # Négatif = DEBIT
    currency=currency,
    entry_type=LedgerEntryType.DEBIT,
)

# Ligne 221-227: CREDIT WALLET_AVAILABLE
credit_entry = LedgerEntry(
    operation_id=operation.id,
    account_id=available_account_id,  # WALLET_AVAILABLE
    amount=amount,  # Positif = CREDIT
    currency=currency,
    entry_type=LedgerEntryType.CREDIT,
)
```

**Operation Type**: `RELEASE_FUNDS`

**Ledger Entries**:
- DEBIT WALLET_BLOCKED: -amount
- CREDIT WALLET_AVAILABLE: +amount

**Impact sur wallet**:
- `blocked_balance` → diminue
- `available_balance` → augmente
- `total_balance` → inchangé

---

## RÉSUMÉ — FLOW COMPLET

### 1. Deposit Webhook (Zand → Backend)

```
POST /webhooks/zand/deposit
  ↓
zand_deposit_webhook()
  ↓
record_deposit_blocked()
  ↓
Operation: DEPOSIT_AED (COMPLETED)
├─ CREDIT WALLET_BLOCKED (+amount)
└─ DEBIT INTERNAL_OMNIBUS (-amount)
```

**Résultat**:
- `blocked_balance` += amount
- `available_balance` = inchangé
- `locked_balance` = inchangé
- `total_balance` += amount

### 2. Compliance Release (Admin → Backend)

```
POST /admin/v1/compliance/release
  ↓
release_funds()
  ↓
release_compliance_funds()
  ↓
Operation: RELEASE_FUNDS (COMPLETED)
├─ DEBIT WALLET_BLOCKED (-amount)
└─ CREDIT WALLET_AVAILABLE (+amount)
```

**Résultat**:
- `blocked_balance` -= amount
- `available_balance` += amount
- `locked_balance` = inchangé
- `total_balance` = inchangé

### 3. User Investment (User → Backend)

```
POST /api/v1/offers/{offer_id}/invest
  ↓
lock_funds_for_investment()
  ↓
Operation: INVEST_EXCLUSIVE (COMPLETED)
├─ DEBIT WALLET_AVAILABLE (-amount)
└─ CREDIT WALLET_LOCKED (+amount)
```

**Résultat**:
- `available_balance` -= amount
- `locked_balance` += amount
- `blocked_balance` = inchangé
- `total_balance` = inchangé

---

## TABLEAU COMPARATIF — OPERATIONS

| Opération | Type | DEBIT Account | CREDIT Account | Wallet Impact |
|-----------|------|---------------|----------------|---------------|
| Deposit (Zand) | DEPOSIT_AED | INTERNAL_OMNIBUS | WALLET_BLOCKED | blocked_balance ↑ |
| Compliance Release | RELEASE_FUNDS | WALLET_BLOCKED | WALLET_AVAILABLE | blocked ↓, available ↑ |
| Invest Offer | INVEST_EXCLUSIVE | WALLET_AVAILABLE | WALLET_LOCKED | available ↓, locked ↑ |
| Vault Deposit | VAULT_DEPOSIT | WALLET_AVAILABLE | VAULT_POOL_CASH | available ↓ |
| Vault Withdraw | VAULT_WITHDRAW_EXECUTED | VAULT_POOL_CASH | WALLET_AVAILABLE | available ↑ |

---

## FICHIERS RÉFÉRENCÉS

- `backend/app/api/webhooks/zand.py` (webhook endpoint)
- `backend/app/api/v1/webhooks/zandbank.py` (simulation DEV)
- `backend/app/services/fund_services.py` (record_deposit_blocked, release_compliance_funds)
- `backend/app/api/admin/compliance.py` (release endpoint)
- `backend/app/core/ledger/models.py` (OperationType.DEPOSIT_AED)

---

## CONFIRMATIONS FINALES

✅ **Deposit webhook crédite WALLET_BLOCKED** (pas WALLET_LOCKED)
✅ **Operation type est DEPOSIT_AED** (pas DEPOSIT_FIAT)
✅ **Aucune logique de lock utilisateur appliquée** (pas d'appel à lock_funds_for_investment)
✅ **Compliance release move BLOCKED → AVAILABLE** (via RELEASE_FUNDS operation)

**Date**: 2025-01-26
**Version**: 1.0
