# SYSTEM WALLETS — CANONICAL DOCUMENTATION

**Date**: 2025-01-26  
**Version**: 1.0

---

## DÉFINITION

Un **System Wallet** est un wallet système (propriété de SYSTEM, pas d'un utilisateur) scoped par un Offer ou un Vault.

- **owner_type**: SYSTEM (représenté par `user_id=None` dans la table `accounts`)
- **scope_type**: OFFER ou VAULT
- **scope_id**: `offer_id` ou `vault_id`
- **currency**: 'AED' (pour l'instant)
- **Buckets**: AVAILABLE / LOCKED / BLOCKED (3 compartiments)

---

## STOCKAGE (TABLE `accounts`)

Les system wallets sont stockés dans la table `accounts` existante, avec les règles suivantes:

### Colonnes utilisées

| Colonne | Valeur pour System Wallet |
|---------|---------------------------|
| `user_id` | `NULL` (system account) |
| `currency` | Currency code (ex: "AED") |
| `account_type` | `OFFER_POOL_AVAILABLE/LOCKED/BLOCKED` ou `VAULT_POOL_CASH/LOCKED/BLOCKED` |
| `vault_id` | `NULL` (pour offers) ou `vault_id` (pour vaults) |
| `offer_id` | `NULL` (pour vaults) ou `offer_id` (pour offers) |

### Mapping AccountType → Bucket

#### Offers

| Bucket | AccountType |
|--------|-------------|
| AVAILABLE | `OFFER_POOL_AVAILABLE` |
| LOCKED | `OFFER_POOL_LOCKED` |
| BLOCKED | `OFFER_POOL_BLOCKED` |

#### Vaults

| Bucket | AccountType | Note |
|--------|-------------|------|
| AVAILABLE | `VAULT_POOL_CASH` | **Rétrocompatibilité**: gardé tel quel pour compatibilité avec code existant |
| LOCKED | `VAULT_POOL_LOCKED` | Nouveau |
| BLOCKED | `VAULT_POOL_BLOCKED` | Nouveau |

**Important**: `VAULT_POOL_CASH` reste l'AccountType pour le bucket AVAILABLE des vaults pour assurer la rétrocompatibilité avec le code existant (vault_service.py, vault_helpers.py).

---

## RÈGLES D'UNICITÉ

### Contrainte DB

**UniqueConstraint**: `(account_type, user_id, vault_id, offer_id, currency)`

**Note**: En PostgreSQL, `NULL != NULL`, donc cette contrainte permet plusieurs lignes avec des valeurs NULL.  
On s'appuie sur la logique application-level "get or create" pour éviter les doublons.

### Application-Level

Les helpers `ensure_offer_system_wallet()` et `ensure_vault_system_wallet()` utilisent une logique "get or create" avec filtres stricts:

```python
account = db.query(Account).filter(
    Account.account_type == bucket_account_type,
    Account.offer_id == offer_id,  # ou vault_id
    Account.currency == currency,
    Account.user_id.is_(None),  # System account
    Account.vault_id.is_(None),  # Pour offers
    # ou Account.offer_id.is_(None) pour vaults
).first()
```

Si l'account existe, retourner son ID. Sinon, créer et retourner.

---

## HELPERS (Single Source of Truth)

### Offers

**Fichier**: `backend/app/services/system_wallet_helpers.py`

```python
ensure_offer_system_wallet(db, offer_id, currency) -> Dict[str, UUID]
# Crée les 3 buckets (AVAILABLE, LOCKED, BLOCKED) et retourne leurs IDs

get_or_create_offer_pool_account(db, offer_id, currency, bucket_account_type) -> UUID
# Crée un bucket spécifique pour un offer

get_offer_system_wallet_balances(db, offer_id, currency) -> Dict[str, Decimal]
# Retourne les balances des 3 buckets
```

### Vaults

```python
ensure_vault_system_wallet(db, vault_id, currency) -> Dict[str, UUID]
# Crée les 3 buckets (AVAILABLE=VAULT_POOL_CASH, LOCKED, BLOCKED) et retourne leurs IDs

get_or_create_vault_pool_account(db, vault_id, currency, account_type) -> UUID
# Crée un bucket spécifique pour un vault

get_vault_system_wallet_balances(db, vault_id, currency) -> Dict[str, Decimal]
# Retourne les balances des 3 buckets
```

**Important**: Le bucket AVAILABLE utilise `VAULT_POOL_CASH` (rétrocompatibilité).

---

## BALANCES

Les balances sont **calculées dynamiquement** depuis le ledger:

```python
balance = SUM(ledger_entries.amount) WHERE account_id = account.id
```

**Pas de colonne `balance`** dans la table `accounts` (accounts sont immutables).

Utiliser `get_account_balance(db, account_id)` depuis `app/services/wallet_helpers.py`.

---

## EXEMPLES

### Offer System Wallet

```python
from app.services.system_wallet_helpers import ensure_offer_system_wallet, get_offer_system_wallet_balances

# Créer les 3 buckets
wallet = ensure_offer_system_wallet(db, offer_id, "AED")
# Returns: {
#   "available": UUID(...),
#   "locked": UUID(...),
#   "blocked": UUID(...)
# }

# Obtenir les balances
balances = get_offer_system_wallet_balances(db, offer_id, "AED")
# Returns: {
#   "available": Decimal("10000.00"),
#   "locked": Decimal("5000.00"),
#   "blocked": Decimal("0.00")
# }
```

### Vault System Wallet

```python
from app.services.system_wallet_helpers import ensure_vault_system_wallet, get_vault_system_wallet_balances

# Créer les 3 buckets (AVAILABLE = VAULT_POOL_CASH)
wallet = ensure_vault_system_wallet(db, vault_id, "AED")
# Returns: {
#   "available": UUID(...),  # AccountType = VAULT_POOL_CASH
#   "locked": UUID(...),     # AccountType = VAULT_POOL_LOCKED
#   "blocked": UUID(...)     # AccountType = VAULT_POOL_BLOCKED
# }

# Obtenir les balances
balances = get_vault_system_wallet_balances(db, vault_id, "AED")
# Returns: {
#   "available": Decimal("50000.00"),  # Depuis VAULT_POOL_CASH
#   "locked": Decimal("0.00"),
#   "blocked": Decimal("0.00")
# }
```

---

## ADMIN API

### GET `/api/v1/admin/offers/{offer_id}/system-wallet`

**Response**:
```json
{
  "scope_type": "OFFER",
  "scope_id": "123e4567-e89b-12d3-a456-426614174000",
  "currency": "AED",
  "available": "10000.00",
  "locked": "5000.00",
  "blocked": "0.00"
}
```

### GET `/api/v1/admin/vaults/{vault_code}/system-wallet`

**Response**:
```json
{
  "scope_type": "VAULT",
  "scope_id": "123e4567-e89b-12d3-a456-426614174001",
  "currency": "AED",
  "available": "50000.00",  // Depuis VAULT_POOL_CASH
  "locked": "0.00",
  "blocked": "0.00"
}
```

---

## MIGRATIONS

**Migration**: `2025_01_26_0200-add_system_wallets_offer_id_and_extend_account_types.py`

**Changements**:
1. Ajoute `offer_id` colonne (nullable UUID FK vers `offers.id`)
2. Étend `AccountType` enum avec:
   - `VAULT_POOL_LOCKED`
   - `VAULT_POOL_BLOCKED`
   - `OFFER_POOL_AVAILABLE`
   - `OFFER_POOL_LOCKED`
   - `OFFER_POOL_BLOCKED`
3. Ajoute index composite `ix_accounts_type_offer_currency`
4. Ajoute `UniqueConstraint` sur `(account_type, user_id, vault_id, offer_id, currency)`

**Commandes**:
```bash
cd backend
alembic upgrade head
alembic current  # Vérifier la version
```

---

## RÉTROCOMPATIBILITÉ

### Vaults

Le code existant utilise `VAULT_POOL_CASH` directement:

```python
# Code existant (vault_helpers.py)
get_or_create_vault_pool_cash_account(db, vault_id, currency)
```

**Compatibilité**: `VAULT_POOL_CASH` est maintenant le bucket AVAILABLE du system wallet.  
Le helper `get_or_create_vault_pool_cash_account()` continue de fonctionner et crée le bucket AVAILABLE du system wallet.

**Migration code** (optionnel, non-breaking):
- Utiliser `ensure_vault_system_wallet()` pour créer tous les buckets
- Utiliser `get_vault_system_wallet_balances()` pour obtenir toutes les balances

### Offers

Les offers n'avaient pas de system wallet avant, donc pas de rétrocompatibilité à gérer.

---

## TESTS

**Fichier**: `backend/tests/test_system_wallets.py`

**Tests couverts**:
1. ✅ `ensure_offer_system_wallet` crée 3 accounts avec `user_id=None` et `offer_id` set
2. ✅ `ensure_vault_system_wallet` crée VAULT_POOL_CASH si missing + VAULT_POOL_LOCKED/BLOCKED
3. ✅ Appeler `ensure_*` deux fois ne crée pas de doublons
4. ✅ `get_offer_system_wallet_balances` retourne les balances
5. ✅ `get_vault_system_wallet_balances` retourne les balances
6. ✅ Vault pool cash (VAULT_POOL_CASH) est utilisé comme bucket AVAILABLE

---

## FICHIERS MODIFIÉS

- ✅ `backend/app/core/accounts/models.py` (AccountType enum, Account model avec offer_id)
- ✅ `backend/app/services/system_wallet_helpers.py` (nouveau fichier)
- ✅ `backend/app/api/admin/vaults.py` (endpoint GET /vaults/{code}/system-wallet)
- ✅ `backend/app/api/admin/offers.py` (endpoint GET /offers/{id}/system-wallet)
- ✅ `backend/alembic/versions/2025_01_26_0200-add_system_wallets_offer_id_and_extend_account_types.py` (migration)
- ✅ `backend/tests/test_system_wallets.py` (nouveau fichier)

---

## NOTES IMPORTANTES

1. **Pas de breaking changes**: Le code existant pour vaults continue de fonctionner (`VAULT_POOL_CASH`).
2. **Immutable accounts**: Les accounts sont immutables, les balances sont calculées depuis le ledger.
3. **NULL handling**: PostgreSQL `NULL != NULL`, donc on s'appuie sur application-level "get or create" pour éviter doublons.
4. **Backward compatibility**: `VAULT_POOL_CASH` reste l'AccountType pour le bucket AVAILABLE des vaults.
