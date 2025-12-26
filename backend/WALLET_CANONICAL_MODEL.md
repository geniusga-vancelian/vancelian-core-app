# WALLET CANONICAL MODEL — Vancelian (AED)

> Objectif : figer la logique **AVAILABLE / LOCKED / BLOCKED** et les mouvements comptables "source of truth" pour éviter toute régression.

## Règle d'or
✅ **Seul `AVAILABLE` est bougeable** (invest, subscribe, withdraw, transfer).  
Tout ce qui n'est pas bougeable est dans **LOCKED** (produit/vesting/invest) ou **BLOCKED** (compliance/rails).

---

## États Wallet

| État | AccountType / Bucket | Sens | Bougeable ? | Qui décide |
|------|----------------------|------|-------------|-----------|
| AVAILABLE | `WALLET_AVAILABLE` | fonds libres | ✅ oui | utilisateur |
| LOCKED | `WALLET_LOCKED` | fonds immobilisés (produit / vesting / invest) | ❌ non | utilisateur / produit |
| BLOCKED | `WALLET_BLOCKED` (ou équivalent) | fonds en attente compliance / rails fiat | ❌ non | système / compliance |

> Note: on ne met **jamais** un dépôt fiat ZAND dans `LOCKED`.  
> `LOCKED` n'est jamais "compliance".

---

## Flows canoniques (double-entry)

### 1) Dépôt fiat (ZAND webhook)
**But :** fonds reçus mais pas encore libérés compliance.

- CREDIT : `WALLET_BLOCKED`
- (contrepartie interne selon ton modèle — souvent "external/clearing" dans Operation/Ledger)

Transition attendue après validation :
- `WALLET_BLOCKED → WALLET_AVAILABLE`

✅ Impact UI :
- available_balance : inchangé
- blocked_balance : ↑
- total_balance : ↑

---

### 2) Release compliance
**But :** rendre dépensable/investissable un dépôt qui était en review.

- DEBIT : `WALLET_BLOCKED`
- CREDIT : `WALLET_AVAILABLE`
- OperationType : `RELEASE_FUNDS` (ou ton type existant)

✅ Impact UI :
- blocked_balance : ↓
- available_balance : ↑
- total_balance : constant

---

### 3) Investissement Offer Exclusive (canonique existant)
**But :** immobilisation produit décidée par l'utilisateur.

- DEBIT : `WALLET_AVAILABLE`
- CREDIT : `WALLET_LOCKED`
- OperationType : `INVEST_EXCLUSIVE`
- Idempotency : via `InvestmentIntent.idempotency_key`
- Invariant : double-entry somme = 0

✅ Impact UI :
- available_balance : ↓
- locked_balance : ↑
- total_balance : constant

---

## Flows Vaults (à implémenter)

### 4) Coffre FLEX — subscribe (entrée)
**But :** entrer dans un coffre mutualisé à liquidité dépendante de la poche cash.

- DEBIT : `WALLET_AVAILABLE`
- CREDIT : `VAULT_POOL_CASH` (compte système scoped par `vault_id`)
- OperationType (proposé) : `VAULT_SUBSCRIBE_FLEX`
- Effets :
  - `vault.cash_balance` ↑
  - `vault.total_aum` ↑
  - `vault_account.principal` ↑

✅ Impact UI :
- available_balance : ↓
- total_balance : constant (si on considère vault position comme partie du patrimoine)
- La position coffre est affichée séparément (principal)

### 5) Coffre FLEX — withdraw (sortie)
**Cas A : cash pool suffisant**
- DEBIT : `VAULT_POOL_CASH`
- CREDIT : `WALLET_AVAILABLE`
- OperationType : `VAULT_WITHDRAW_EXECUTED`
- Effets :
  - `vault.cash_balance` ↓
  - `vault.total_aum` ↓
  - `vault_account.principal` ↓

**Cas B : cash pool insuffisant**
- créer `withdrawal_request` status `PENDING` (FIFO)
- aucune écriture ledger au moment de la demande

Admin : `process_pending_withdrawals()` exécute FIFO avec locks.

---

### 6) Coffre AVENIR — vesting 1 an (choix produit)
**But :** immobiliser au wallet-level avec maturité automatique.

#### Subscribe (entrée)
- DEBIT : `WALLET_AVAILABLE`
- CREDIT : `WALLET_LOCKED`
- OperationType (proposé) : `VAULT_SUBSCRIBE_AVENIR`
- Créer un enregistrement de vesting (recommandé) :
  - `wallet_locks` / `lock_records`
  - reason = `VAULT_AVENIR_VESTING`
  - locked_until = now + 365 jours
  - reference = vault_account / vault_subscription

#### Maturité (auto)
- DEBIT : `WALLET_LOCKED`
- CREDIT : `WALLET_AVAILABLE`
- OperationType : `VAULT_VESTING_MATURE`
- Ne libérer que les locks reason = `VAULT_AVENIR_VESTING` expirés.

✅ Remarque :
`WALLET_LOCKED` est aussi utilisé par Offers, donc la **distinction par reason** est obligatoire
pour éviter de libérer de l'argent investi dans une Offer.

---

## Invariants & Concurrency

- Toutes les écritures ledger doivent respecter le double-entry (somme = 0).
- Utiliser `SELECT ... FOR UPDATE` sur les lignes critiques :
  - Wallet accounts (available/locked/blocked)
  - Vault row
  - Vault pool cash account
  - Withdrawal requests FIFO via `FOR UPDATE SKIP LOCKED`
- Pas de `commit()` interne dans les fonctions services : commit uniquement au niveau endpoint / unit of work.

---

## Glossaire
- **LOCKED** : immobilisé produit/vesting/invest (jamais compliance)
- **BLOCKED** : compliance / rails fiat / under review
- **VAULT_POOL_CASH** : compte système de la poche cash du coffre (mutualisée), scoped par `vault_id`

