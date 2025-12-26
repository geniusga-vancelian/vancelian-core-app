# Rapport: Fonction Canonique d'Investissement dans une Offre

**Date:** 2025-12-25  
**Objectif:** Identifier la fonction canonique qui exécute l'investissement depuis le wallet AED jusqu'à la création des écritures comptables.

---

## A) Fonction Canonique d'Investissement

### 1. Endpoint Client

**Fichier:** `backend/app/api/v1/offers.py`  
**Ligne:** 372-483  
**Route:** `POST /api/v1/offers/{offer_id}/invest`  
**Handler:** `invest_in_offer_endpoint()`

```python
async def invest_in_offer_endpoint(
    offer_id: UUID,
    request: InvestInOfferRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> OfferInvestmentResponse
```

### 2. Service Principal

**Fichier:** `backend/app/services/offers/service_v1_1.py`  
**Ligne:** 71-299  
**Fonction:** `invest_in_offer_v1_1()`

**Signature:**
```python
def invest_in_offer_v1_1(
    *,
    db: Session,
    user_id: UUID,
    offer_id: UUID,
    amount: Decimal,
    currency: str,
    idempotency_key: str | None = None,
) -> tuple[InvestmentIntent, Decimal]
```

**Chaîne d'appel:**
```
invest_in_offer_endpoint()
  └─> invest_in_offer_v1_1()
        └─> lock_funds_for_investment()
```

### 3. Fonction de Mouvement de Fonds

**Fichier:** `backend/app/services/fund_services.py`  
**Ligne:** 273-382  
**Fonction:** `lock_funds_for_investment()`

**Signature:**
```python
def lock_funds_for_investment(
    *,
    db: Session,
    user_id: UUID,
    currency: str,
    amount: Decimal,
    transaction_id: Optional[UUID] = None,
    reason: Optional[str] = None,
) -> Operation
```

**Appelée par:**
- `invest_in_offer_v1_1()` (ligne 244)

---

## B) Contrat Comptable

### 1. Types d'Opérations (OperationType)

**Fichier:** `backend/app/core/ledger/models.py`

```python
class OperationType(str, enum.Enum):
    # ... autres types ...
    INVEST_EXCLUSIVE = "INVEST_EXCLUSIVE"  # Utilisé pour investir dans une offre
```

### 2. Types de Comptes (AccountType)

**Fichier:** `backend/app/core/accounts/models.py`

```python
class AccountType(str, enum.Enum):
    WALLET_AVAILABLE = "WALLET_AVAILABLE"   # Fonds disponibles
    WALLET_BLOCKED = "WALLET_BLOCKED"       # Fonds bloqués (compliance)
    WALLET_LOCKED = "WALLET_LOCKED"         # Fonds verrouillés (investis)
    INTERNAL_OMNIBUS = "INTERNAL_OMNIBUS"   # Compte système
```

### 3. Types d'Écritures Comptables (LedgerEntryType)

**Fichier:** `backend/app/core/ledger/models.py`

```python
class LedgerEntryType(str, enum.Enum):
    DEBIT = "DEBIT"    # Débit (montant négatif)
    CREDIT = "CREDIT"  # Crédit (montant positif)
```

### 4. Statuts d'Opération (OperationStatus)

**Fichier:** `backend/app/core/ledger/models.py`

```python
class OperationStatus(str, enum.Enum):
    COMPLETED = "COMPLETED"  # Utilisé pour lock_funds_for_investment
    FAILED = "FAILED"
    PENDING = "PENDING"
    CANCELLED = "CANCELLED"
```

### 5. Mouvements de Wallet

**Fonction:** `lock_funds_for_investment()` (lignes 273-382)

**Comptes affectés:**
1. **WALLET_AVAILABLE** (débit): Diminue de `amount`
2. **WALLET_LOCKED** (crédit): Augmente de `amount`

**Écritures comptables créées:**
1. **LedgerEntry (DEBIT)**
   - `account_id`: WALLET_AVAILABLE account
   - `amount`: `-amount` (négatif)
   - `entry_type`: `LedgerEntryType.DEBIT`

2. **LedgerEntry (CREDIT)**
   - `account_id`: WALLET_LOCKED account
   - `amount`: `amount` (positif)
   - `entry_type`: `LedgerEntryType.CREDIT`

### 6. Opération Créée

**Operation:**
- `type`: `OperationType.INVEST_EXCLUSIVE`
- `status`: `OperationStatus.COMPLETED`
- `idempotency_key`: `None` (pas d'idempotency dans cette fonction)
- `metadata`: `{'currency': currency, 'reason': reason}`

### 7. Vérifications Avant Mouvement

1. **Validation montant:** `amount > 0`
2. **Vérification balance:** `available_balance >= amount`
   - Utilise `get_account_balance(db, available_account_id)`
   - Lève `InsufficientBalanceError` si insuffisant

---

## C) Ordre des Écritures DB (Pseudo-code)

```
1. Validation: amount > 0
2. ensure_wallet_accounts(user_id, currency) → {WALLET_AVAILABLE, WALLET_LOCKED}
3. get_account_balance(WALLET_AVAILABLE) → vérifie disponibilité
4. INSERT Operation (type=INVEST_EXCLUSIVE, status=COMPLETED)
5. INSERT LedgerEntry (DEBIT WALLET_AVAILABLE, amount=-amount)
6. INSERT LedgerEntry (CREDIT WALLET_LOCKED, amount=+amount)
7. INSERT AuditLog (action=FUNDS_LOCKED_FOR_INVESTMENT)
8. validate_double_entry_invariant(operation_id)
9. recompute_transaction_status(transaction_id) → LOCKED
10. COMMIT (dans lock_funds_for_investment)
```

**Note:** Dans `invest_in_offer_v1_1()`, l'ordre complet est:
```
1. SELECT Offer ... FOR UPDATE (lock offer row)
2. Check idempotency (InvestmentIntent)
3. Validate offer (status, currency)
4. Create InvestmentIntent (status=PENDING)
5. Compute allocated_amount = min(requested, remaining)
6. IF allocated > 0:
    6a. INSERT Transaction (type=INVESTMENT, status=INITIATED)
    6b. lock_funds_for_investment() → Operation + LedgerEntries + COMMIT
    6c. UPDATE InvestmentIntent (status=CONFIRMED, allocated_amount, operation_id)
    6d. UPDATE Offer (invested_amount += allocated, committed_amount += allocated)
7. ELSE:
    7a. UPDATE InvestmentIntent (status=REJECTED, allocated_amount=0)
8. COMMIT (appelant invest_in_offer_endpoint)
```

---

## D) Ce qu'il faut Réutiliser pour Vaults/Coffres

### 1. Recommandations

**✅ À réutiliser:**
- **Même pattern Operation + LedgerEntry** (double-entry accounting)
- **Même validation double-entry invariant** (`validate_double_entry_invariant`)
- **Même pattern de compte** (WALLET_AVAILABLE, WALLET_LOCKED, etc.)
- **Même gestion d'erreurs** (`InsufficientBalanceError`, `ValidationError`)
- **Même audit trail** (`AuditLog`)

**❌ À éviter:**
- **Ne PAS modifier les comptes wallet existants**
  - Vaults utilisent leur propre compte système: `VAULT_POOL_CASH` (à ajouter si pas encore existant)
- **Créer de nouveaux types d'opération si nécessaire**
  - Proposer: `VAULT_DEPOSIT` et `VAULT_WITHDRAW_EXECUTED` (à ajouter à `OperationType` enum)

### 2. Mapping Proposé pour Vaults

#### Vault Deposit (analogue à invest_in_offer mais avec VAULT_POOL_CASH)

**Fonction proposée:** `record_vault_deposit()`

**Mouvements:**
- **DEBIT:** USER WALLET_AVAILABLE (diminue)
- **CREDIT:** VAULT_POOL_CASH account (augmente)

**Operation:**
- `type`: `OperationType.VAULT_DEPOSIT` (existant)
- `status`: `OperationStatus.COMPLETED`

#### Vault Withdrawal Executed (exécution immédiate)

**Fonction proposée:** `execute_vault_withdrawal()`

**Mouvements:**
- **DEBIT:** VAULT_POOL_CASH account (diminue)
- **CREDIT:** USER WALLET_AVAILABLE (augmente)

**Operation:**
- `type`: `OperationType.VAULT_WITHDRAW_EXECUTED` (à créer)
- `status`: `OperationStatus.COMPLETED`

#### Vault Withdrawal Pending (mise en file d'attente FIFO)

**Pas de mouvement de ledger** (contrairement à invest_in_offer)
- Création d'un `WithdrawalRequest` (status=PENDING)
- Pas d'opération comptable
- Pas de mouvement de fonds

**Exécution différée (admin):**
- Traitement FIFO par un processus admin
- Appelle `execute_vault_withdrawal()` quand le vault a suffisamment de liquidité

### 3. Pièges Identifiés

#### 1. Idempotency

**Offres:** Utilise `idempotency_key` dans `InvestmentIntent`  
**Vaults:** À implémenter au niveau `WithdrawalRequest` si nécessaire

**Recommandation:** Utiliser une clé basée sur `(user_id, vault_id, amount, reference)` pour éviter les doublons.

#### 2. Arrondi Decimal

**Offres:** Quantize à 2 décimales (via Pydantic validators)  
**Vaults:** Utiliser le même pattern (`Decimal('0.01').quantize()`)

**Exemple:**
```python
@field_validator('amount')
@classmethod
def validate_amount(cls, v: Decimal) -> Decimal:
    return v.quantize(Decimal('0.01'))
```

#### 3. Frontières de Transaction

**Offres:** 
- `lock_funds_for_investment()` fait son propre `COMMIT`
- `invest_in_offer_v1_1()` fait un `COMMIT` supplémentaire

**Vaults:**
- **Attention:** Si `lock_funds_for_investment()` est utilisé comme référence, il fait un `COMMIT` interne
- Pour Vaults, **recommandation:** Créer une fonction qui **ne fait PAS de COMMIT** (comme `record_deposit_blocked` qui ne fait pas de COMMIT dans certaines versions)
- Ou: S'assurer que toutes les écritures (Operation, LedgerEntries, VaultAccount update) sont dans la même transaction

**Exemple de pattern recommandé:**
```python
def record_vault_deposit(...) -> Operation:
    # Create Operation
    # Create LedgerEntries
    # Update VaultAccount
    # Validate double-entry
    # NO COMMIT - caller commits
    return operation
```

#### 4. Concurrency (Verrouillage de Lignes)

**Offres:** Utilise `SELECT ... FOR UPDATE` sur `Offer` row  
**Vaults:** Recommandation similaire:
- Lock `Vault` row: `SELECT ... FOR UPDATE`
- Lock `VaultAccount` row: `SELECT ... FOR UPDATE`
- Lock `WithdrawalRequest` rows: `SELECT ... FOR UPDATE SKIP LOCKED` (FIFO)

#### 5. Vérification de Balance

**Offres:** Vérifie `WALLET_AVAILABLE` balance avant mouvement  
**Vaults:** Deux vérifications nécessaires:
1. **User balance:** Vérifier `WALLET_AVAILABLE >= amount` (pour withdrawal)
2. **Vault pool balance:** Vérifier `VAULT_POOL_CASH balance >= amount` (pour withdrawal executed)

**Pattern:**
```python
available_balance = get_account_balance(db, user_available_account_id)
if available_balance < amount:
    raise InsufficientBalanceError(...)

vault_balance = get_account_balance(db, vault_pool_account_id)
if vault_balance < amount:
    # Create WithdrawalRequest PENDING instead
    return create_pending_withdrawal(...)
```

#### 6. Statut de Transaction

**Offres:** Utilise `Transaction` model + `recompute_transaction_status()`  
**Vaults:** Pas besoin de `Transaction` pour les opérations internes de vault
- Les `Operation` sont suffisantes
- Si besoin de tracking user-facing, créer un `VaultTransaction` séparé (optionnel)

---

## E) Résumé des Fonctions Clés

| Fonction | Fichier | Ligne | Rôle |
|----------|---------|-------|------|
| `invest_in_offer_endpoint()` | `app/api/v1/offers.py` | 379 | Endpoint API |
| `invest_in_offer_v1_1()` | `app/services/offers/service_v1_1.py` | 71 | Service principal (logique métier) |
| `lock_funds_for_investment()` | `app/services/fund_services.py` | 273 | **Fonction canonique** (mouvement de fonds + ledger) |
| `ensure_wallet_accounts()` | `app/services/wallet_helpers.py` | 14 | Création/comptes wallet |
| `get_account_balance()` | `app/services/wallet_helpers.py` | 57 | Lecture balance compte |
| `validate_double_entry_invariant()` | `app/utils/ledger_validator.py` | ? | Validation comptable |

---

## F) Conclusion

**Fonction canonique à utiliser comme référence:**  
👉 **`lock_funds_for_investment()`** dans `backend/app/services/fund_services.py:273-382`

**Pattern à répliquer pour Vaults:**
1. Validation `amount > 0`
2. `ensure_wallet_accounts()` / `get_vault_pool_cash_account()`
3. Vérification balance
4. Création `Operation`
5. Création 2x `LedgerEntry` (DEBIT + CREDIT)
6. Création `AuditLog`
7. Validation double-entry invariant
8. **PAS de COMMIT interne** (laisser l'appelant committer)

**Différences clés Vaults vs Offers:**
- Vaults utilisent `VAULT_POOL_CASH` (compte système) au lieu de `WALLET_LOCKED` (compte user)
- Vaults peuvent avoir des withdrawals en PENDING (pas de mouvement ledger)
- Vaults nécessitent un traitement FIFO pour les withdrawals en attente

