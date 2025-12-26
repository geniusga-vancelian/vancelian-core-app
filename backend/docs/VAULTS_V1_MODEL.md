# Vaults V1 Model - Positions + Vesting (Sans Rendement)

**Date:** 2025-01-26  
**Version:** v1  
**Status:** ✅ Implemented

---

## Objectif

Ce document explique le modèle V1 des coffres (FLEX + AVENIR) aligné avec le système Wallet et la Wallet Matrix. Cette version implémente :
- Positions client (deposit/withdraw)
- Vesting AVENIR (1 an, locked)
- FIFO queue pour withdrawals
- Intégration Wallet Matrix (FLEX → available, AVENIR → locked)

**Non inclus dans V1:**
- Rendement
- Allocation vers DeFi/offres exclusives
- Autres mécanismes de yield

---

## Architecture

### 1. Types de Coffres

**FLEX (Flexible Vault):**
- Liquidité immédiate
- Pas de vesting
- Position affichée dans colonne **AVAILABLE** de Wallet Matrix
- Withdrawals exécutés immédiatement si pool cash suffisant, sinon FIFO queue

**AVENIR (Avenir Vault):**
- Vesting 1 an (365 jours)
- Position affichée dans colonne **LOCKED** de Wallet Matrix
- Withdrawals bloqués avant maturité (403 LOCKED)
- Après maturité, même comportement que FLEX

### 2. System Wallets

Chaque vault a un **system wallet** (compte système):
- Type: `VAULT_POOL_CASH`
- Scope: `vault_id`
- Currency: `AED` (pour l'instant)

**Balances:**
- `available`: Cash disponible pour withdrawals
- `locked`: 0 (pas utilisé pour V1)
- `blocked`: 0 (compliance uniquement)

**Source de vérité:** Ledger (via `get_vault_cash_balance()`)

### 3. Positions Client

**Table: `vault_accounts`**
- `user_id` + `vault_id` (UNIQUE)
- `principal`: Total deposits (ne diminue que sur withdrawal)
- `available_balance`: Principal - pending withdrawals (pour V1, = principal)
- `locked_until`: Pour AVENIR, date de maturité (now + 365 jours)

**Règle:** Un user peut avoir une position dans FLEX et AVENIR simultanément.

### 4. Liability Tracking (wallet_locks)

**Pour AVENIR uniquement:**
- Création d'un `WalletLock` lors du deposit
- `reason = VAULT_AVENIR_VESTING`
- `reference_type = VAULT`
- `reference_id = vault_id`
- `status = ACTIVE` (jusqu'à withdrawal)

**Pour FLEX:**
- Pas de `wallet_locks` (position affichée directement depuis `vault_account.principal`)

**Source de vérité Wallet Matrix:**
- FLEX: `vault_account.principal` → colonne `available`
- AVENIR: `SUM(wallet_locks.amount WHERE status=ACTIVE)` → colonne `locked`

---

## Flow de Deposit

### FLEX Deposit

**Endpoint:** `POST /api/v1/vaults/FLEX/deposits`

**Flow:**
1. Validation: amount > 0, vault ACTIVE, user balance suffisant
2. Lock vault row (`FOR UPDATE`)
3. Lock user WALLET_AVAILABLE account (`FOR UPDATE`)
4. Lock vault VAULT_POOL_CASH account (`FOR UPDATE`)
5. Création `Operation` (VAULT_DEPOSIT, COMPLETED)
6. Ledger entries:
   - DEBIT user WALLET_AVAILABLE (-amount)
   - CREDIT vault VAULT_POOL_CASH (+amount)
7. Validation double-entry invariant
8. Update `VaultAccount.principal += amount`
9. Update `VaultAccount.available_balance += amount`
10. **Pas de wallet_lock créé** (FLEX → available column)

**Double-entry:** ✅ Balance

### AVENIR Deposit

**Endpoint:** `POST /api/v1/vaults/AVENIR/deposits`

**Flow:**
1-7. Identique à FLEX
8. Update `VaultAccount.principal += amount`
9. Update `VaultAccount.available_balance += amount`
10. **Set `locked_until = max(locked_until, now + 365 days)`**
11. **Création `WalletLock`:**
    ```python
    wallet_lock = WalletLock(
        user_id=user_id,
        currency=currency,
        amount=amount,
        reason=LockReason.VAULT_AVENIR_VESTING.value,
        reference_type=ReferenceType.VAULT.value,
        reference_id=vault.id,
        status=LockStatus.ACTIVE.value,
        intent_id=None,  # Not applicable for vaults
        operation_id=operation.id,  # For idempotency
    )
    ```
12. Idempotency: vérifier si `operation_id` existe déjà (pas de doublon)

**Double-entry:** ✅ Balance

---

## Flow de Withdrawal

### FLEX Withdrawal

**Endpoint:** `POST /api/v1/vaults/FLEX/withdrawals`

**Flow:**
1. Validation: amount > 0, vault ACTIVE, `vault_account.principal >= amount`
2. Lock vault row (`FOR UPDATE`)
3. Lock `VaultAccount` row (`FOR UPDATE`)
4. Lock accounts (`FOR UPDATE`)
5. **Check vault cash balance:**
   - Si `vault_cash_balance >= amount`:
     - Execute immediately:
       - Création `Operation` (VAULT_WITHDRAW_EXECUTED, COMPLETED)
       - Ledger entries:
         - DEBIT vault VAULT_POOL_CASH (-amount)
         - CREDIT user WALLET_AVAILABLE (+amount)
       - Update `VaultAccount.principal -= amount`
       - Création `WithdrawalRequest` (status=EXECUTED)
   - Sinon:
     - Création `WithdrawalRequest` (status=PENDING, FIFO queue)

**Double-entry:** ✅ Balance (si EXECUTED)

### AVENIR Withdrawal

**Endpoint:** `POST /api/v1/vaults/AVENIR/withdrawals`

**Flow:**
1. Validation: amount > 0, vault ACTIVE, `vault_account.principal >= amount`
2. **Check vesting lock:**
   - Si `vault_account.locked_until > now` → **403 VAULT_LOCKED**
   - Si `vault.locked_until > now` → **403 VAULT_LOCKED**
3. Si maturité atteinte, même flow que FLEX
4. **Release wallet_locks proportionnellement:**
   - Get active locks (ordered by `created_at`, oldest first)
   - Pour chaque lock:
     - Si `lock.amount <= remaining_to_release`:
       - Mark `lock.status = RELEASED`
       - `lock.released_at = now`
     - Sinon (partial):
       - Mark `lock.status = RELEASED`
       - Create new lock avec `amount = lock.amount - remaining_to_release`
       - Status = ACTIVE

**Double-entry:** ✅ Balance (si EXECUTED)

---

## FIFO Admin Processor

### Endpoint

**POST** `/api/v1/admin/vaults/{vault_code}/withdrawals/process`

**Flow:**
1. Lock vault row (`FOR UPDATE`)
2. Get pending requests (ordered by `created_at`, `SKIP LOCKED`)
3. Pour chaque request (tant que vault cash suffisant):
   - Lock `VaultAccount` row (`FOR UPDATE`)
   - Check principal >= amount
   - Check vault cash >= amount
   - Execute withdrawal (même flow que withdrawal immédiat)
   - Mark request status = EXECUTED
   - Pour AVENIR: release wallet_locks (même logique)
4. Return `processed_count`, `remaining_count`

**Concurrency:** ✅ Safe (FOR UPDATE SKIP LOCKED)

---

## Wallet Matrix Integration

### Source de Vérité

**FLEX:**
```python
# From vault_account.principal
available = vault_account.principal
locked = Decimal("0.00")
```

**AVENIR:**
```python
# From wallet_locks (source of truth)
vault_locked_total = db.query(
    func.sum(WalletLock.amount)
).filter(
    WalletLock.user_id == user_id,
    WalletLock.reference_type == "VAULT",
    WalletLock.reference_id == vault.id,
    WalletLock.reason == LockReason.VAULT_AVENIR_VESTING.value,
    WalletLock.status == LockStatus.ACTIVE.value,
    WalletLock.currency == currency,
).scalar()

available = Decimal("0.00")
locked = vault_locked_total  # Fallback to principal if locks not present
```

**AED Row:**
- `locked` = `"0.00"` (toujours)
- Les montants locked sont reclassifiés sous les instruments (FLEX/AVENIR)

---

## API Routes

### Client Routes

**GET** `/api/v1/vaults/{vault_code}/me`
- Returns: `VaultAccountMeResponse` (principal, available_balance, locked_until, vault snapshot)

**POST** `/api/v1/vaults/{vault_code}/deposits`
- Request: `DepositRequest` (amount, currency)
- Response: `DepositResponse` (operation_id, vault_account_id, vault snapshot)

**POST** `/api/v1/vaults/{vault_code}/withdrawals`
- Request: `WithdrawRequest` (amount, currency, reason)
- Response: `WithdrawResponse` (request_id, status, operation_id, vault snapshot)

**GET** `/api/v1/vaults/{vault_code}/withdrawals`
- Response: `WithdrawalListResponse` (list of user's withdrawal requests)

### Admin Routes

**GET** `/api/v1/admin/vaults`
- Response: `AdminVaultsListResponse` (list of vaults with pending stats)

**GET** `/api/v1/admin/vaults/{vault_code}/portfolio`
- Response: `AdminPortfolioResponse` (vault snapshot, accounts_count, system_wallet, pending_withdrawals_count)

**GET** `/api/v1/admin/vaults/{vault_code}/withdrawals?status=PENDING`
- Response: `WithdrawalListResponse` (list of withdrawal requests, filtered by status)

**POST** `/api/v1/admin/vaults/{vault_code}/withdrawals/process`
- Response: `ProcessWithdrawalsResponse` (processed_count, remaining_count)

**Auth:**
- Client routes: `require_user_role()`
- Admin routes: `require_admin_role()`

---

## Exemples

### Exemple 1: FLEX Deposit

**Action:** User dépose 5,000 AED dans FLEX

**Résultat:**
1. User WALLET_AVAILABLE: -5,000
2. Vault VAULT_POOL_CASH: +5,000
3. `VaultAccount.principal`: +5,000
4. **Pas de wallet_lock créé**

**Wallet Matrix:**
- AED (USER): available=..., locked=0.00
- COFFRE — FLEX: available=5,000.00, locked=0.00

### Exemple 2: AVENIR Deposit

**Action:** User dépose 3,000 AED dans AVENIR

**Résultat:**
1. User WALLET_AVAILABLE: -3,000
2. Vault VAULT_POOL_CASH: +3,000
3. `VaultAccount.principal`: +3,000
4. `VaultAccount.locked_until`: now + 365 days
5. **WalletLock créé:** amount=3,000, status=ACTIVE

**Wallet Matrix:**
- AED (USER): available=..., locked=0.00
- COFFRE — AVENIR: available=0.00, locked=3,000.00

### Exemple 3: AVENIR Withdraw Avant Maturité

**Action:** User tente de retirer 1,000 AED d'AVENIR avant maturité

**Résultat:**
- **403 VAULT_LOCKED** (error code)

### Exemple 4: AVENIR Withdraw Après Maturité

**Action:** User retire 1,000 AED d'AVENIR après maturité

**Résultat:**
1. Vault VAULT_POOL_CASH: -1,000
2. User WALLET_AVAILABLE: +1,000
3. `VaultAccount.principal`: -1,000
4. **WalletLock released:** oldest ACTIVE lock marked RELEASED (ou partiel si nécessaire)

**Wallet Matrix:**
- COFFRE — AVENIR: available=0.00, locked=2,000.00 (3,000 - 1,000)

### Exemple 5: FIFO Processing

**Action:** Admin process pending withdrawals pour FLEX

**Résultat:**
- Traite requests dans l'ordre `created_at` (oldest first)
- S'arrête quand vault cash insuffisant
- Return `processed_count`, `remaining_count`

---

## Tests

### Tests Disponibles

1. **`test_flex_deposit_decreases_user_available_increases_vault_pool`**
   - Vérifie deposit FLEX: user balance ↓, vault pool ↑, principal ↑
   - Vérifie pas de wallet_lock créé

2. **`test_avenir_deposit_creates_wallet_lock_and_sets_locked_until`**
   - Vérifie deposit AVENIR: même que FLEX + wallet_lock créé + locked_until set

3. **`test_avenir_withdraw_before_maturity_returns_403`**
   - Vérifie withdrawal AVENIR avant maturité → 403 LOCKED

4. **`test_flex_withdraw_when_pool_sufficient_executes`**
   - Vérifie withdrawal FLEX avec cash suffisant → EXECUTED immédiatement

5. **`test_flex_withdraw_when_insufficient_creates_pending`**
   - Vérifie withdrawal FLEX avec cash insuffisant → PENDING

6. **`test_wallet_matrix_shows_flex_in_available_avenir_in_locked`**
   - Vérifie Wallet Matrix: FLEX → available, AVENIR → locked (depuis wallet_locks)

---

## Migration

**Tables existantes (déjà créées):**
- `vaults` (via migration `create_vaults_20251225`)
- `vault_accounts` (via migration `create_vaults_20251225`)
- `withdrawal_requests` (via migration `create_vaults_20251225`)
- `wallet_locks` (via migration `create_wallet_locks_20250126`)

**Pas de nouvelle migration nécessaire pour V1.**

---

## Notes Techniques

- **Concurrency safe:** Tous les updates utilisent `FOR UPDATE` sur les rows critiques
- **Double-entry invariant:** Validé après chaque operation
- **Idempotency:** `wallet_locks` utilise `operation_id` pour éviter doublons
- **Source de vérité:** Ledger pour balances, `wallet_locks` pour AVENIR locked amount
- **FIFO:** `SKIP LOCKED` pour éviter deadlocks en concurrence
- **AED row locked = 0:** Toujours, conformément au canon métier

---

## Checklist de Validation

- [ ] FLEX deposit crée position, pas de wallet_lock
- [ ] AVENIR deposit crée position + wallet_lock + locked_until
- [ ] AVENIR withdraw avant maturité → 403
- [ ] FLEX withdraw avec cash suffisant → EXECUTED
- [ ] FLEX withdraw avec cash insuffisant → PENDING
- [ ] Admin process FIFO exécute correctement
- [ ] Wallet Matrix: FLEX → available, AVENIR → locked (depuis wallet_locks)
- [ ] AED row locked = 0.00 (toujours)

---

**Dernière mise à jour:** 2025-01-26

