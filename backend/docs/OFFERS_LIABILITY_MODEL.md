# Offers Liability Model - Wallet Locks

**Date:** 2025-01-26  
**Version:** v1  
**Status:** ✅ Implemented

---

## Objectif

Ce document explique le modèle de liability (passif) pour les investissements dans les offers, basé sur la table `wallet_locks`. Ce modèle permet de :
- Tracer quels fonds sont verrouillés pour quel instrument (Offer/Vault)
- Fournir la source de vérité pour la Wallet Matrix
- Permettre aux admins de voir les liabilities totales par offer

---

## Architecture

### 1. Double Couche : Ledger + Metadata

**Ledger (source de vérité comptable):**
- Les mouvements de fonds sont enregistrés dans `LedgerEntry`
- `WALLET_AVAILABLE` → `WALLET_LOCKED` (via `Operation` type `INVEST_EXCLUSIVE`)
- Le ledger est immuable et suit les règles de double-entry accounting

**Wallet Locks (metadata de liability):**
- Table `wallet_locks` qui ajoute une couche de metadata
- Indique **pourquoi** les fonds sont verrouillés (reason)
- Indique **où** ils sont alloués (reference_type + reference_id)
- Permet l'idempotency via `intent_id`

### 2. Pourquoi AED row locked = 0.00 ?

**Règle métier canonique:**
- Les montants "locked" dans `WALLET_LOCKED` ne sont **pas** affichés dans la ligne AED(USER)
- Ils sont **reclassifiés** sous l'instrument (Offer/Vault) qui les a verrouillés
- Cela permet une vue "décomposition" de l'exposition, pas une "somme confondue"

**Exemple:**
```
User a 10,000 AED available et a investi 5,000 dans Offer X

Wallet Matrix affiche:
- AED (USER): available=10,000, locked=0.00, blocked=0
- OFFRE — X: available=0, locked=5,000, blocked=0

Pas:
- AED (USER): available=10,000, locked=5,000  ❌ (incorrect)
```

---

## Modèle de Données

### Table: wallet_locks

```sql
CREATE TABLE wallet_locks (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ,
    user_id UUID NOT NULL REFERENCES users(id),
    currency TEXT NOT NULL DEFAULT 'AED',
    amount NUMERIC(20,2) NOT NULL CHECK (amount > 0),
    reason TEXT NOT NULL,  -- 'OFFER_INVEST', 'VAULT_AVENIR_VESTING', etc.
    reference_type TEXT NOT NULL,  -- 'OFFER', 'VAULT'
    reference_id UUID NOT NULL,  -- offer_id or vault_id
    status TEXT NOT NULL DEFAULT 'ACTIVE',  -- 'ACTIVE', 'RELEASED'
    intent_id UUID UNIQUE REFERENCES investment_intents(id),  -- For idempotency
    operation_id UUID REFERENCES operations(id),
    released_at TIMESTAMPTZ NULL
);

-- Indexes
CREATE INDEX ix_wallet_locks_reference ON wallet_locks(reference_type, reference_id, reason, status);
CREATE INDEX ix_wallet_locks_user_status ON wallet_locks(user_id, status);
CREATE UNIQUE INDEX uq_wallet_locks_intent_id ON wallet_locks(intent_id);
```

### Enums

**LockReason:**
- `OFFER_INVEST` - Fonds verrouillés pour investissement dans une offer
- `VAULT_AVENIR_VESTING` - Fonds verrouillés dans AVENIR vault (vesting period)

**ReferenceType:**
- `OFFER` - Référence à une Offer
- `VAULT` - Référence à un Vault

**LockStatus:**
- `ACTIVE` - Lock actif (fonds verrouillés)
- `RELEASED` - Lock libéré (fonds déverrouillés, ex: offer fermée, withdrawal)

---

## Flow d'Investissement

### 1. User investit dans une offer

**Endpoint:** `POST /api/v1/offers/{offer_id}/invest`

**Flow:**
1. Validation offer (status, currency, remaining amount)
2. Création `InvestmentIntent` (status=PENDING)
3. Calcul `allocated_amount` (min(requested, remaining))
4. Si `allocated > 0`:
   - Création `Transaction` (type=INVESTMENT, status=INITIATED)
   - Appel `lock_funds_for_investment()`:
     - Création `Operation` (INVEST_EXCLUSIVE, COMPLETED)
     - Création `LedgerEntry`: DEBIT WALLET_AVAILABLE, CREDIT WALLET_LOCKED
     - Création `AuditLog`
   - Mise à jour `InvestmentIntent` (status=CONFIRMED, allocated_amount, operation_id)
   - **Création `WalletLock`** (idempotent via intent_id):
     ```python
     wallet_lock = WalletLock(
         user_id=user_id,
         currency=currency,
         amount=allocated,
         reason=LockReason.OFFER_INVEST.value,
         reference_type=ReferenceType.OFFER.value,
         reference_id=offer_id,
         status=LockStatus.ACTIVE.value,
         intent_id=intent.id,  # For idempotency
         operation_id=operation.id,
     )
     ```
   - Mise à jour `Offer.invested_amount`

### 2. Idempotency

**Protection:** `intent_id` est UNIQUE dans `wallet_locks`

**Règle:**
- Si un `WalletLock` existe déjà pour `intent_id`, on ne crée pas de doublon
- Cela garantit qu'un même investissement n'est compté qu'une fois

**Code:**
```python
existing_lock = db.query(WalletLock).filter(
    WalletLock.intent_id == intent.id
).first()

if not existing_lock:
    # Create wallet_lock
    ...
```

---

## Wallet Matrix - Source de Vérité

### OFFER_USER Rows

**Source de vérité:** `wallet_locks` table (pas `InvestmentIntent`)

**Query:**
```python
user_offer_locks_query = db.query(
    WalletLock.reference_id.label("offer_id"),
    func.sum(WalletLock.amount).label("total_invested")
).filter(
    WalletLock.user_id == user_id,
    WalletLock.reason == LockReason.OFFER_INVEST.value,
    WalletLock.reference_type == "OFFER",
    WalletLock.status == LockStatus.ACTIVE.value,
    WalletLock.currency == currency,
).group_by(WalletLock.reference_id).all()
```

**Résultat:**
- Une ligne `OFFRE — <name>` par offer où le user a investi
- `locked` = somme des `wallet_locks` ACTIVE pour cette offer
- `available` = `0.00`
- `blocked` = `0.00`

### Pourquoi wallet_locks et pas InvestmentIntent ?

**Avantages:**
1. **Séparation des responsabilités:**
   - `InvestmentIntent` = intent/request (peut être REJECTED)
   - `WalletLock` = liability actuelle (seulement ACTIVE)

2. **Extensibilité:**
   - Future: `VAULT_AVENIR_VESTING` peut utiliser le même modèle
   - Future: `RELEASED` status pour tracker historique

3. **Performance:**
   - Index optimisé pour queries par `reference_type` + `reference_id`
   - Pas besoin de joindre avec `InvestmentIntent` pour Wallet Matrix

---

## Admin View - Offer Portfolio

### Endpoint

**GET** `/api/v1/admin/offers/{offer_id}/portfolio`

**Response:**
```json
{
  "offer_id": "123e4567-e89b-12d3-a456-426614174000",
  "currency": "AED",
  "system_wallet": {
    "available": "50000.00",
    "locked": "0.00",
    "blocked": "0.00"
  },
  "clients_locked_total": "25000.00"
}
```

**Calcul:**
- `system_wallet`: Balances du wallet système de l'offer (via `get_offer_system_wallet_balances`)
- `clients_locked_total`: `SUM(wallet_locks.amount) WHERE reference_id=offer_id AND status=ACTIVE AND reason=OFFER_INVEST`

**Usage:**
- Permet aux admins de voir:
  - Combien de fonds clients sont verrouillés pour cette offer
  - Les balances du wallet système de l'offer
  - La cohérence entre les deux (validation)

---

## Mouvements Ledger (Non Modifiés)

**Important:** Ce modèle **ne change pas** les mouvements ledger existants.

**Flow actuel (inchangé):**
1. `lock_funds_for_investment()` crée:
   - `Operation` (INVEST_EXCLUSIVE, COMPLETED)
   - `LedgerEntry` DEBIT WALLET_AVAILABLE
   - `LedgerEntry` CREDIT WALLET_LOCKED

**Ajout (nouveau):**
- `WalletLock` record créé après le ledger (metadata seulement)

**Pas de changement:**
- Les comptes `WALLET_AVAILABLE` et `WALLET_LOCKED` fonctionnent comme avant
- Les règles de double-entry accounting restent inchangées
- Les `AuditLog` restent inchangés

---

## Exemples

### Exemple 1: Investissement simple

**Action:** User investit 5,000 AED dans Offer X

**Résultat:**
1. `LedgerEntry`: DEBIT WALLET_AVAILABLE -5,000, CREDIT WALLET_LOCKED +5,000
2. `WalletLock`: 
   - `user_id` = user.id
   - `amount` = 5,000
   - `reason` = "OFFER_INVEST"
   - `reference_id` = offer_x.id
   - `status` = "ACTIVE"

**Wallet Matrix:**
- AED (USER): available=..., locked=0.00, blocked=...
- OFFRE — X: available=0.00, locked=5,000.00, blocked=0.00

### Exemple 2: Investissements multiples

**Action:** 
- User investit 5,000 dans Offer A
- User investit 3,000 dans Offer B

**Résultat:**
- 2 `WalletLock` records (un par offer)
- `WALLET_LOCKED` balance = 8,000 (somme)

**Wallet Matrix:**
- AED (USER): locked=0.00 (toujours)
- OFFRE — A: locked=5,000.00
- OFFRE — B: locked=3,000.00

**Admin Portfolio (Offer A):**
- `clients_locked_total` = 5,000.00 (seulement pour Offer A)

---

## Tests

### Tests Disponibles

1. **`test_invest_offer_creates_wallet_lock_once`**
   - Vérifie qu'un investissement crée un `WalletLock`
   - Vérifie l'idempotency (pas de doublon)

2. **`test_wallet_matrix_uses_wallet_locks_for_offer_row`**
   - Vérifie que Wallet Matrix utilise `wallet_locks` (pas `InvestmentIntent`)
   - Vérifie que les montants sont corrects

3. **`test_admin_offer_portfolio_clients_locked_total`**
   - Vérifie que l'endpoint admin calcule correctement `clients_locked_total`
   - Vérifie avec plusieurs users

---

## Migration

**Fichier:** `backend/alembic/versions/2025_01_26_0300-create_wallet_locks_table.py`

**Commande:**
```bash
cd backend
alembic upgrade head
```

**Rollback:**
```bash
alembic downgrade -1
```

---

## Notes Techniques

- **Pas de refactor:** Les flows ledger existants ne sont pas modifiés
- **Metadata seulement:** `wallet_locks` est une couche metadata, pas une source comptable
- **Idempotency:** Garantie via `intent_id` UNIQUE
- **Performance:** Index optimisés pour queries Wallet Matrix et Admin Portfolio
- **Extensibilité:** Modèle prêt pour Vaults (AVENIR vesting) et autres raisons futures

---

## Checklist de Validation

- [ ] Migration appliquée (`alembic upgrade head`)
- [ ] Invest offer crée `WalletLock` (test: `test_invest_offer_creates_wallet_lock_once`)
- [ ] Wallet Matrix utilise `wallet_locks` (test: `test_wallet_matrix_uses_wallet_locks_for_offer_row`)
- [ ] Admin portfolio calcule `clients_locked_total` (test: `test_admin_offer_portfolio_clients_locked_total`)
- [ ] AED row locked = 0.00 (toujours)
- [ ] Pas de double comptage

---

**Dernière mise à jour:** 2025-01-26

