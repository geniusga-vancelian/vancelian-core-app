# Rapport: Découverte Vaults/Coffres (État Actuel du Code)

**Date:** 2025-12-25  
**Objectif:** Inventaire de ce qui existe déjà pour les Vaults/Coffres et ce qui doit être créé.

---

## A) État du Backend

### 1. Structure de Dossiers

**Répertoires identifiés:**
- ✅ `backend/app/core/vaults/` - Existe mais **VIDE** (seulement `__pycache__/`)
- ❌ Aucun fichier source Python trouvé pour vaults

**Fichiers Python compilés trouvés (indiquent une implémentation précédente):**
```
app/auth/__pycache__/vault_auth.cpython-312.pyc
app/schemas/__pycache__/vaults.cpython-312.pyc
app/api/v1/__pycache__/vaults.cpython-312.pyc
app/api/admin/__pycache__/vaults.cpython-312.pyc
app/services/__pycache__/vault_service.cpython-312.pyc
app/services/__pycache__/vault_helpers.cpython-312.pyc
```

**Conclusion:** Il y avait une implémentation Vaults précédente qui a été supprimée, mais les fichiers `.pyc` et des migrations Alembic restent:
- `backend/alembic/versions/__pycache__/2025_12_25_1500-create_vaults_tables.cpython-312.pyc`
- `backend/alembic/versions/__pycache__/2025_12_25_1600-extend_accounts_and_operations_for_vaults.cpython-312.pyc`

**Les fichiers sources Python ont été supprimés, donc tout doit être recréé.**

---

### 2. Modèles à Créer

**Fichiers à créer:**

#### Models (`backend/app/core/vaults/models.py`)
- ❌ `Vault` - Modèle pour les coffres (FLEX, AVENIR)
- ❌ `VaultAccount` - Relation user ↔ vault (principal, available balance, locked_until)
- ❌ `WithdrawalRequest` - Demandes de retrait (status PENDING/EXECUTED, FIFO queue)

**Tables à créer via Alembic:**
- `vaults` - Table principale
- `vault_accounts` - Comptes utilisateurs dans les vaults
- `withdrawal_requests` - File d'attente des retraits

---

### 3. Routes/Endpoints à Créer

#### Client API (`backend/app/api/v1/vaults.py`)
**Routes à créer:**
- ❌ `GET /api/v1/vaults/{vault_code}/me` - Récupérer le compte vault de l'utilisateur
- ❌ `POST /api/v1/vaults/{vault_code}/deposits` - Déposer dans un vault
- ❌ `POST /api/v1/vaults/{vault_code}/withdrawals` - Demander un retrait
- ❌ `GET /api/v1/vaults/{vault_code}/withdrawals` - Liste des retraits de l'utilisateur

**Pattern d'auth à utiliser:**
```python
from app.auth.dependencies import require_user_role, get_user_id_from_principal
from app.auth.oidc import Principal

@router.get("/vaults/{vault_code}/me")
async def get_vault_account(
    vault_code: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> VaultAccountResponse:
    user_id = get_user_id_from_principal(principal)
    # ...
```

#### Admin API (`backend/app/api/admin/vaults.py`)
**Routes à créer:**
- ❌ `GET /api/v1/admin/vaults` - Liste tous les vaults (déjà présent dans le rapport précédent ?)
- ❌ `GET /api/v1/admin/vaults/{vault_code}/portfolio` - Détails du portfolio vault
- ❌ `GET /api/v1/admin/vaults/{vault_code}/withdrawals?status=PENDING` - Liste retraits en attente
- ❌ `POST /api/v1/admin/vaults/{vault_code}/withdrawals/process` - Traiter les retraits FIFO

**Pattern d'auth à utiliser:**
```python
from app.auth.dependencies import require_admin_role
from app.auth.oidc import Principal

@router.get("/admin/vaults")
async def list_vaults(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_role()),
) -> VaultsListResponse:
    # ...
```

---

### 4. Services à Créer

**Fichiers à créer:**

#### Service Principal (`backend/app/services/vault_service.py`)
- ❌ `VaultService` - Classe ou fonctions pour:
  - `deposit(user_id, vault_code, amount, currency)` - Déposer
  - `withdraw(user_id, vault_code, amount, currency)` - Retirer (immédiat ou PENDING)
  - `process_pending_withdrawals(vault_code)` - Traiter FIFO (admin)
  - `get_vault_account(user_id, vault_code)` - Récupérer compte

#### Helpers (`backend/app/services/vault_helpers.py`)
- ❌ `get_user_cash_account(db, user_id, currency)` - Récupérer compte WALLET_AVAILABLE
- ❌ `get_vault_pool_cash_account(db, vault_id, currency)` - Récupérer/créer compte VAULT_POOL_CASH
- ❌ `get_vault_cash_balance(db, vault_id, currency)` - Balance depuis ledger

---

### 5. Schémas Pydantic à Créer

**Fichier à créer:** `backend/app/schemas/vaults.py`

**Schémas nécessaires:**
- ❌ `VaultSnapshot` - Informations vault (code, name, status, cash_balance, total_aum)
- ❌ `VaultAccountResponse` - Réponse compte vault (principal, available, locked_until, vault_snapshot)
- ❌ `DepositRequest` - Requête dépôt (amount, currency)
- ❌ `DepositResponse` - Réponse dépôt (operation_id, vault_account)
- ❌ `WithdrawalRequest` - Requête retrait (amount, currency)
- ❌ `WithdrawalResponse` - Réponse retrait (request_id, status, operation_id si EXECUTED)
- ❌ `VaultPortfolioResponse` - Portfolio admin (cash_balance, total_aum, recent_ledger_entries)
- ❌ `ProcessWithdrawalsResponse` - Réponse traitement FIFO (processed_count, remaining_count)

---

### 6. Enums/Constants à Étendre

#### OperationType (`backend/app/core/ledger/models.py`)
**À ajouter:**
- ❌ `VAULT_DEPOSIT = "VAULT_DEPOSIT"` - Dépôt dans un vault
- ❌ `VAULT_WITHDRAW_EXECUTED = "VAULT_WITHDRAW_EXECUTED"` - Retrait exécuté

**État actuel:**
```python
class OperationType(str, enum.Enum):
    DEPOSIT_AED = "DEPOSIT_AED"
    INVEST_EXCLUSIVE = "INVEST_EXCLUSIVE"
    RELEASE_FUNDS = "RELEASE_FUNDS"
    REVERSAL_DEPOSIT = "REVERSAL_DEPOSIT"
    ADJUSTMENT = "ADJUSTMENT"
    REVERSAL = "REVERSAL"
    # VAULT_DEPOSIT et VAULT_WITHDRAW_EXECUTED à ajouter
```

#### AccountType (`backend/app/core/accounts/models.py`)
**À ajouter:**
- ❌ `VAULT_POOL_CASH = "VAULT_POOL_CASH"` - Compte système pour pool de liquidité du vault

**État actuel:**
```python
class AccountType(str, enum.Enum):
    WALLET_AVAILABLE = "WALLET_AVAILABLE"
    WALLET_BLOCKED = "WALLET_BLOCKED"
    WALLET_LOCKED = "WALLET_LOCKED"
    INTERNAL_OMNIBUS = "INTERNAL_OMNIBUS"
    # VAULT_POOL_CASH à ajouter
```

**Note:** Le modèle `Account` devra peut-être être étendu avec un champ `vault_id` (ForeignKey vers `vaults.id`) pour lier les comptes VAULT_POOL_CASH aux vaults spécifiques.

---

### 7. Patterns Ledger/Comptable Existants à Réutiliser

**Fonctions de référence identifiées:**
- ✅ `lock_funds_for_investment()` dans `app/services/fund_services.py:273-382`
- ✅ `record_deposit_blocked()` dans `app/services/fund_services.py:30-157`
- ✅ `release_compliance_funds()` dans `app/services/fund_services.py:160-270`

**Pattern à suivre:**
1. Validation `amount > 0`
2. `ensure_wallet_accounts()` / `get_vault_pool_cash_account()`
3. Vérification balance (`get_account_balance()`)
4. Création `Operation`
5. Création 2x `LedgerEntry` (DEBIT + CREDIT, double-entry)
6. Création `AuditLog`
7. Validation `validate_double_entry_invariant()`
8. **NO COMMIT** (laisser l'appelant committer)

**Fonctions helper existantes:**
- ✅ `ensure_wallet_accounts(db, user_id, currency)` - Crée/compte wallet si nécessaire
- ✅ `get_account_balance(db, account_id)` - Balance depuis ledger
- ✅ `get_wallet_balances(db, user_id, currency)` - Toutes les balances wallet
- ✅ `validate_double_entry_invariant(db, operation_id)` - Validation comptable

---

### 8. Enregistrement des Routes

**Fichiers à modifier:**

#### Client API (`backend/app/api/v1/__init__.py`)
**À ajouter:**
```python
from app.api.v1.vaults import router as vaults_router

router.include_router(vaults_router, tags=["vaults"])
```

#### Admin API (`backend/app/api/admin/__init__.py`)
**À ajouter:**
```python
from app.api.admin.vaults import router as admin_vaults_router

router.include_router(admin_vaults_router)
```

---

## B) État du Frontend-Client

### 1. Dashboard Principal

**Fichier:** `frontend-client/app/page.tsx`

**État actuel:**
- ✅ Wallet AED balance affichée (ligne 82: `apiRequest('api/v1/wallet?currency=AED')`)
- ✅ Bouton "Deposit" (DEV only) - ligne 282-288
- ✅ Modal de dépôt - ligne 449-507
- ✅ Fonction `handleDeposit()` - ligne 169-213

**Endpoints appelés:**
- `GET /api/v1/wallet?currency=AED` - Récupère balance wallet
- `POST /api/v1/webhooks/zandbank/simulate` - Simule dépôt (DEV)

**Fichiers à étendre pour Vaults:**
- ✅ `frontend-client/app/page.tsx` - Dashboard principal
  - Ajouter section "Mes Coffres" avec balances FLEX/AVENIR
  - Ajouter boutons "Déposer" et "Retirer" pour chaque vault
- ❌ `frontend-client/app/vaults/[vault_code]/page.tsx` - Page détail vault (à créer)
- ❌ `frontend-client/components/vaults/DepositModal.tsx` - Modal dépôt vault (à créer)
- ❌ `frontend-client/components/vaults/WithdrawModal.tsx` - Modal retrait vault (à créer)

---

### 2. API Client

**Fichier:** `frontend-client/lib/api.ts`

**État actuel:**
- ✅ `apiRequest()` - Helper générique pour requêtes API
- ✅ `getToken()` / `setToken()` - Gestion tokens (sessionStorage)
- ✅ `depositApi.simulateZandDeposit()` - Simule dépôt ZAND

**À ajouter pour Vaults:**
```typescript
// Types
interface VaultAccount {
  vault_code: string
  principal: string
  available_balance: string
  locked_until: string | null
  vault: {
    code: string
    name: string
    status: string
    cash_balance: string
    total_aum: string
  }
}

interface DepositVaultRequest {
  amount: string
  currency: string
}

interface DepositVaultResponse {
  operation_id: string
  vault_account: VaultAccount
}

// API
export const vaultsApi = {
  getMyVaultAccount: async (vaultCode: string): Promise<VaultAccount> => {
    return apiRequest(`api/v1/vaults/${vaultCode}/me`)
  },
  
  deposit: async (vaultCode: string, payload: DepositVaultRequest): Promise<DepositVaultResponse> => {
    return apiRequest(`api/v1/vaults/${vaultCode}/deposits`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  
  withdraw: async (vaultCode: string, payload: WithdrawVaultRequest): Promise<WithdrawVaultResponse> => {
    return apiRequest(`api/v1/vaults/${vaultCode}/withdrawals`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  
  listMyWithdrawals: async (vaultCode: string): Promise<WithdrawalRequest[]> => {
    return apiRequest(`api/v1/vaults/${vaultCode}/withdrawals`)
  },
}
```

---

## C) Résumé: Ce qui Existe vs Ce qui Doit Être Créé

### ✅ Ce qui EXISTE (Patterns à Réutiliser)

1. **Auth:**
   - ✅ `require_user_role()` - Dépendance FastAPI pour USER
   - ✅ `require_admin_role()` - Dépendance FastAPI pour ADMIN
   - ✅ `get_user_id_from_principal()` - Extraction user_id depuis Principal

2. **Ledger/Comptabilité:**
   - ✅ `Operation` + `LedgerEntry` models
   - ✅ Double-entry accounting pattern
   - ✅ `validate_double_entry_invariant()`
   - ✅ `ensure_wallet_accounts()` / `get_account_balance()`
   - ✅ `lock_funds_for_investment()` comme référence

3. **Frontend:**
   - ✅ Dashboard avec wallet balance
   - ✅ Pattern modal pour dépôt
   - ✅ `apiRequest()` helper avec auth automatique
   - ✅ Gestion d'erreurs avec `parseApiError()`

---

### ❌ Ce qui DOIT ÊTRE CRÉÉ

#### Backend

1. **Models:**
   - ❌ `backend/app/core/vaults/models.py` - Vault, VaultAccount, WithdrawalRequest
   - ❌ `backend/app/core/vaults/__init__.py` - Exports

2. **Services:**
   - ❌ `backend/app/services/vault_service.py` - Logique métier vaults
   - ❌ `backend/app/services/vault_helpers.py` - Helpers (comptes, balances)

3. **Routes:**
   - ❌ `backend/app/api/v1/vaults.py` - API client
   - ❌ `backend/app/api/admin/vaults.py` - API admin

4. **Schémas:**
   - ❌ `backend/app/schemas/vaults.py` - Pydantic schemas

5. **Extensions Enums:**
   - ❌ Ajouter `VAULT_DEPOSIT` et `VAULT_WITHDRAW_EXECUTED` à `OperationType`
   - ❌ Ajouter `VAULT_POOL_CASH` à `AccountType`
   - ❌ Ajouter `vault_id` ForeignKey au modèle `Account` (si nécessaire)

6. **Migrations Alembic:**
   - ❌ Migration pour créer tables `vaults`, `vault_accounts`, `withdrawal_requests`
   - ❌ Migration pour étendre enums `OperationType` et `AccountType`
   - ❌ Migration pour ajouter `vault_id` à `accounts` (si nécessaire)

7. **Enregistrement Routes:**
   - ❌ Ajouter `vaults_router` à `app/api/v1/__init__.py`
   - ❌ Ajouter `admin_vaults_router` à `app/api/admin/__init__.py`

#### Frontend

1. **Pages:**
   - ❌ `frontend-client/app/vaults/[vault_code]/page.tsx` - Page détail vault

2. **Composants:**
   - ❌ `frontend-client/components/vaults/DepositModal.tsx`
   - ❌ `frontend-client/components/vaults/WithdrawModal.tsx`
   - ❌ `frontend-client/components/vaults/VaultCard.tsx` - Carte vault sur dashboard

3. **API Client:**
   - ❌ Ajouter `vaultsApi` à `frontend-client/lib/api.ts`

4. **Extension Dashboard:**
   - ❌ Section "Mes Coffres" dans `frontend-client/app/page.tsx`

---

## D) Checklist de Création (Ordre Recommandé)

### Phase 1: Backend - Foundation
- [ ] Créer `backend/app/core/vaults/models.py` (Vault, VaultAccount, WithdrawalRequest)
- [ ] Créer `backend/app/core/vaults/__init__.py`
- [ ] Étendre `OperationType` enum (VAULT_DEPOSIT, VAULT_WITHDRAW_EXECUTED)
- [ ] Étendre `AccountType` enum (VAULT_POOL_CASH)
- [ ] Ajouter `vault_id` ForeignKey au modèle `Account` (si nécessaire)
- [ ] Migration Alembic: créer tables + étendre enums

### Phase 2: Backend - Services
- [ ] Créer `backend/app/services/vault_helpers.py` (get_user_cash_account, get_vault_pool_cash_account, get_vault_cash_balance)
- [ ] Créer `backend/app/services/vault_service.py` (VaultService avec deposit, withdraw, process_pending_withdrawals)

### Phase 3: Backend - API
- [ ] Créer `backend/app/schemas/vaults.py` (Pydantic schemas)
- [ ] Créer `backend/app/api/v1/vaults.py` (routes client)
- [ ] Créer `backend/app/api/admin/vaults.py` (routes admin)
- [ ] Enregistrer routers dans `__init__.py`

### Phase 4: Frontend
- [ ] Ajouter `vaultsApi` à `frontend-client/lib/api.ts`
- [ ] Créer composants vault (DepositModal, WithdrawModal, VaultCard)
- [ ] Étendre dashboard (`frontend-client/app/page.tsx`) avec section coffres
- [ ] Créer page détail vault (`frontend-client/app/vaults/[vault_code]/page.tsx`)

---

## E) Références de Code Existantes

### Patterns Auth à Réutiliser

**Endpoint wallet (exemple):**
```python
# backend/app/api/v1/wallet.py:25-52
@router.get("/wallet")
async def get_wallet(
    currency: str = "AED",
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> WalletBalanceResponse:
    user_id = get_user_id_from_principal(principal)
    balances = get_wallet_balances(db, user_id, currency)
    return WalletBalanceResponse(...)
```

### Patterns Ledger à Réutiliser

**Référence: `lock_funds_for_investment()`**
- Fichier: `backend/app/services/fund_services.py:273-382`
- Pattern: Validation → Check balance → Create Operation → Create LedgerEntries → AuditLog → Validate invariant

**Voir rapport:** `backend/CANONICAL_INVEST_FUNCTION_REPORT.md`

---

## F) Notes Importantes

1. **Pas de fichiers sources existants:** Tous les fichiers doivent être créés from scratch (même si des `.pyc` suggèrent une implémentation précédente).

2. **Réutiliser les patterns existants:** 
   - Même structure que `offers` (models, services, routes client/admin)
   - Même pattern ledger que `lock_funds_for_investment()`
   - Même auth que wallet/offers endpoints

3. **Double-entry accounting obligatoire:**
   - Chaque opération crée 2 LedgerEntry (DEBIT + CREDIT)
   - Utiliser `validate_double_entry_invariant()` avant commit
   - Les balances sont calculées depuis le ledger (pas de colonnes `balance` dans les modèles)

4. **Comptes système:**
   - Vault pool = compte `VAULT_POOL_CASH` avec `user_id=None` et `vault_id=<vault_id>`
   - User cash = compte `WALLET_AVAILABLE` (existant)

---

**Rapport généré le:** 2025-12-25  
**Prochaines étapes:** Suivre la checklist Phase 1 → Phase 4

