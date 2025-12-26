# OFFER INVEST — CANONICAL FLOW REPORT

Ce document décrit le flow canonique "Invest in Offer" pour servir de référence lors de l'implémentation de Vaults.

## PHASE 1 — BACKEND: FLOW OFFER (CANON)

### 1. Endpoint

**Route**: `POST /api/v1/offers/{offer_id}/invest`

**Fichier**: `backend/app/api/v1/offers.py` (ligne 373-484)

**Fonction**: `invest_in_offer_endpoint()`

### 2. Request/Response Schema

**Request** (`InvestInOfferRequest`):
```python
{
  "amount": Decimal,      # Montant à investir (> 0)
  "currency": str,        # "AED" (default)
  "idempotency_key": str  # Optionnel, pour éviter doubles investissements
}
```

**Response** (`OfferInvestmentResponse`):
```python
{
  "investment_id": str,              # InvestmentIntent UUID
  "offer_id": str,                   # Offer UUID
  "requested_amount": str,           # Montant demandé
  "accepted_amount": str,            # Montant réellement alloué (peut être < requested si offer presque plein)
  "currency": str,
  "status": str,                     # "PENDING", "CONFIRMED", "REJECTED"
  "offer_committed_amount": str,     # Montant total déjà investi dans l'offer
  "offer_remaining_amount": str,     # Capacité restante
  "created_at": str                  # ISO timestamp
}
```

### 3. Chaîne d'appel complète

```
invest_in_offer_endpoint()
  ↓
invest_in_offer_v1_1()  (backend/app/services/offers/service_v1_1.py:71)
  ↓
lock_funds_for_investment()  (backend/app/services/fund_services.py:273)
  ↓
[DB writes: Operation + LedgerEntries + AuditLog]
```

### 4. Fonction `invest_in_offer_v1_1()` - Détails

**Fichier**: `backend/app/services/offers/service_v1_1.py`

**Flow interne**:
1. Validation `amount > 0`
2. **Lock offer row**: `SELECT ... FOR UPDATE` (CRITIQUE pour concurrence)
3. Check idempotency (après lock, dans même transaction)
4. Validation offer.status == LIVE + currency match
5. Calcul `remaining = max_amount - invested_amount`
6. Si `remaining <= 0`: créer InvestmentIntent REJECTED, raise `OfferFullError`
7. Calcul `allocated = min(requested_amount, remaining)` (partial fill support)
8. Créer `InvestmentIntent` avec status PENDING
9. Si `allocated > 0`:
   - Créer `Transaction` (type INVESTMENT, status INITIATED)
   - Appeler `lock_funds_for_investment()` → crée Operation + LedgerEntries
   - Mettre à jour InvestmentIntent.status = CONFIRMED
   - Mettre à jour `offer.invested_amount += allocated` (UPDATE atomique)
10. Si `allocated == 0`: InvestmentIntent.status = REJECTED
11. Retourner `(InvestmentIntent, remaining_after)`

**Note importante**: 
- Le caller (endpoint) doit faire `db.commit()` après l'appel
- Tous les writes sont atomiques dans la même transaction
- `remaining_amount` ne doit JAMAIS devenir négatif (contrainte DB)

### 5. Fonction `lock_funds_for_investment()` - Détails

**Fichier**: `backend/app/services/fund_services.py` (ligne 273-382)

**Flow interne**:
1. Validation `amount > 0`
2. `ensure_wallet_accounts()` pour obtenir account IDs
3. Check balance: `get_account_balance(available_account_id) >= amount`
4. Créer `Operation`:
   - type: `OperationType.INVEST_EXCLUSIVE`
   - status: `OperationStatus.COMPLETED`
   - idempotency_key: None (pas d'idempotency au niveau Operation)
5. Créer 2 `LedgerEntry` (double-entry):
   - DEBIT WALLET_AVAILABLE: `amount = -amount` (négatif)
   - CREDIT WALLET_LOCKED: `amount = +amount` (positif)
6. Créer `AuditLog`
7. Valider invariant double-entry: `validate_double_entry_invariant()`
8. **COMMIT interne** (`db.commit()`) ⚠️
9. Retourner `Operation`

**Note**: Cette fonction COMMIT en interne, donc elle ne peut pas être utilisée dans une transaction plus large sans modification.

### 6. Ledger/Accounting — Mouvements exacts

**Accounts touchés**:
- `WALLET_AVAILABLE` (user_id, currency) → DEBIT
- `WALLET_LOCKED` (user_id, currency) → CREDIT

**Operation**:
- Type: `INVEST_EXCLUSIVE`
- Status: `COMPLETED`
- Idempotency: Pas d'idempotency au niveau Operation (idempotency gérée au niveau InvestmentIntent)

**Ledger Entries** (double-entry):
```
Operation: INVEST_EXCLUSIVE (COMPLETED)
├─ LedgerEntry 1:
│  ├─ account_id: WALLET_AVAILABLE (user_id, currency)
│  ├─ amount: -allocated_amount (négatif = DEBIT)
│  ├─ entry_type: DEBIT
│  └─ currency: "AED"
│
└─ LedgerEntry 2:
   ├─ account_id: WALLET_LOCKED (user_id, currency)
   ├─ amount: +allocated_amount (positif = CREDIT)
   ├─ entry_type: CREDIT
   └─ currency: "AED"
```

**Vérification double-entry**:
- Sum of all amounts for this operation MUST equal 0
- Validated via `validate_double_entry_invariant(operation.id)`

### 7. Transactions/Concurrency

**SELECT ... FOR UPDATE**:
- `SELECT * FROM offers WHERE id = offer_id FOR UPDATE`
- Lock acquis sur la row offer AVANT toute vérification/allocation
- Empêche double allocation concurrente

**Commit**:
- ⚠️ **IMPORTANT**: `lock_funds_for_investment()` fait un `db.commit()` interne (ligne 381)
- `invest_in_offer_v1_1()` ne commit PAS (caller doit commit)
- Endpoint fait `db.commit()` après appel à `invest_in_offer_v1_1()` (ligne 406)
- **Impact**: Le commit de `lock_funds_for_investment()` committe déjà l'Operation + LedgerEntries
- Le commit de l'endpoint committe le reste (InvestmentIntent, Transaction, Offer.invested_amount)
- **Conséquence**: Pas de transaction atomique complète - si erreur après `lock_funds_for_investment()`, les fonds sont déjà lockés mais InvestmentIntent peut être PENDING

**Idempotency**:
- Vérifiée au niveau `InvestmentIntent.idempotency_key` (UNIQUE constraint)
- Check fait APRÈS lock offer (dans même transaction)
- Si idempotency_key existe déjà → retourner InvestmentIntent existant

**Double spend protection**:
- Lock offer row → vérifie `remaining_amount` → alloue → UPDATE atomique
- Balance check dans `lock_funds_for_investment()` AVANT création Operation
- Pas de SELECT FOR UPDATE sur accounts (balance check via `get_account_balance()` qui fait un SUM)

### 8. Status Transitions

**InvestmentIntent**:
- PENDING → CONFIRMED (si allocated > 0)
- PENDING → REJECTED (si allocated == 0 ou erreur)

**Transaction**:
- INITIATED → LOCKED (après Operation INVEST_EXCLUSIVE COMPLETED)
- INITIATED → FAILED (si InsufficientBalanceError)

**Operation**:
- Toujours créé avec status COMPLETED (pas de transition)

### 9. Modèles DB touchés

1. **Offer** (UPDATE):
   - `invested_amount += allocated_amount`
   - `committed_amount += allocated_amount` (sync)

2. **InvestmentIntent** (INSERT):
   - `offer_id`, `user_id`, `requested_amount`, `allocated_amount`
   - `status`, `idempotency_key`, `operation_id`

3. **Transaction** (INSERT):
   - `user_id`, `type = INVESTMENT`, `status = INITIATED/LOCKED/FAILED`
   - `transaction_metadata` (JSON avec offer_id, offer_code, etc.)

4. **Operation** (INSERT via `lock_funds_for_investment()`):
   - `type = INVEST_EXCLUSIVE`, `status = COMPLETED`
   - `transaction_id`, `operation_metadata`

5. **LedgerEntry** (INSERT x2):
   - DEBIT WALLET_AVAILABLE
   - CREDIT WALLET_LOCKED

6. **AuditLog** (INSERT):
   - Action: "FUNDS_LOCKED_FOR_INVESTMENT"

---

## PHASE 2 — FRONTEND-CLIENT: INVEST OFFER

### 1. Pages/Fichiers

**Page principale**: `frontend-client/app/invest/[id]/page.tsx`

**Composant**: `frontend-client/components/offers/OfferInvestCard.tsx`

**API wrapper**: `frontend-client/lib/api.ts` (ligne 237-340)

### 2. API Call

**Méthode**: `offersApi.invest(offerId, payload)`

**Payload**:
```typescript
{
  amount: string,           // "1000.00"
  currency: string,         // "AED"
  idempotency_key?: string  // UUID v4 généré côté client
}
```

**Headers**:
```
Authorization: Bearer <token>
Content-Type: application/json
```

### 3. Code Frontend (extrait)

```typescript
// frontend-client/app/invest/[id]/page.tsx
const handleInvest = async () => {
  const idempotencyKey = crypto.randomUUID()
  const result = await offersApi.invest(offerId, {
    amount: amount,
    currency: offer.currency,
    idempotency_key: idempotencyKey,
  })
  
  setInvestmentResult(result)
  setAmount("")
  
  // Reload offer and wallet after successful investment
  setTimeout(() => {
    loadData()  // Recharge offer details
    // Wallet reload via parent component
  }, 1000)
}
```

### 4. Refresh Dashboard

Après investissement réussi:
- `loadData()` recharge les détails de l'offer (montant restant, etc.)
- Le wallet est rafraîchi via le parent component (dashboard)
- Les transactions sont rechargées pour afficher le nouveau mouvement

### 5. Impact Wallet UI

**Avant investissement**:
- Available: X AED
- Locked: Y AED
- Total: X + Y AED

**Après investissement (montant `allocated`)**:
- Available: X - allocated AED
- Locked: Y + allocated AED
- Total: (X + Y) AED (inchangé)

**Champs impactés**:
- `available_balance` (GET /api/v1/wallet) → diminue
- `locked_balance` (GET /api/v1/wallet) → augmente
- `total_balance` (GET /api/v1/wallet) → inchangé

---

## PHASE 3 — TABLEAU RÉCAPITULATIF

### Mouvements Ledger (AVANT → APRÈS)

| Account Type | User ID | Currency | Montant AVANT | Opération | Montant APRÈS | Entry Type |
|--------------|---------|----------|---------------|-----------|---------------|------------|
| WALLET_AVAILABLE | user_123 | AED | 10000.00 | DEBIT -1000.00 | 9000.00 | DEBIT |
| WALLET_LOCKED | user_123 | AED | 5000.00 | CREDIT +1000.00 | 6000.00 | CREDIT |

**Vérification**: DEBIT(-1000) + CREDIT(+1000) = 0 ✅

### Mapping Wallet UI Impact

| Champ Wallet UI | Avant | Après | Source |
|-----------------|-------|-------|--------|
| `available_balance` | 10000.00 | 9000.00 | GET /api/v1/wallet → sum(LedgerEntry WHERE account_type=WALLET_AVAILABLE) |
| `locked_balance` | 5000.00 | 6000.00 | GET /api/v1/wallet → sum(LedgerEntry WHERE account_type=WALLET_LOCKED) |
| `total_balance` | 15000.00 | 15000.00 | available + locked (inchangé) |
| `blocked_balance` | 0.00 | 0.00 | Non impacté |

---

## PHASE 4 — PIÈGES / CONTRAINTES POUR VAULTS

### ⚠️ Points critiques à répliquer

1. **SELECT ... FOR UPDATE**:
   - Lock la row Vault AVANT vérification cash_balance
   - Empêche double withdrawal concurrent

2. **Idempotency**:
   - Gérer au niveau VaultAccount ou WithdrawalRequest
   - Vérifier APRÈS lock (dans même transaction)

3. **Double-entry invariant**:
   - Toujours valider avec `validate_double_entry_investment()`
   - Sum of amounts MUST = 0

4. **Commit pattern** ⚠️ CRITIQUE:
   - `lock_funds_for_investment()` fait `db.commit()` en interne (ligne 381) → problème de transaction atomique
   - Si erreur après `lock_funds_for_investment()`, les fonds sont déjà lockés mais InvestmentIntent reste PENDING
   - **Pour Vaults**: NE PAS commit dans `deposit_to_vault()` / `request_withdrawal()` / helpers
   - Laisser UNIQUEMENT le caller (endpoint) faire le commit
   - Alternative: Créer une version de `lock_funds_for_investment()` qui ne commit pas (ou paramètre `commit=False`)

5. **Balance check**:
   - Vérifier balance AVANT création Operation
   - Utiliser `get_account_balance()` (SUM des LedgerEntries)

6. **Partial fill**:
   - Offers supporte partial fill (si requested > remaining)
   - Vaults: pas de partial fill (tout ou rien)

7. **Status lifecycle**:
   - InvestmentIntent: PENDING → CONFIRMED/REJECTED
   - Vault withdrawal: PENDING → EXECUTED/CANCELLED

8. **Transaction record**:
   - Offers crée un `Transaction` record
   - Vaults: pas de Transaction record (direct Operation)

### ✅ Différences attendues pour Vaults

1. **Operation types**:
   - Offers: `INVEST_EXCLUSIVE`
   - Vaults: `VAULT_DEPOSIT`, `VAULT_WITHDRAW_EXECUTED`

2. **Account types**:
   - Offers: WALLET_AVAILABLE → WALLET_LOCKED
   - Vaults Deposit: WALLET_AVAILABLE → VAULT_POOL_CASH
   - Vaults Withdraw: VAULT_POOL_CASH → WALLET_AVAILABLE

3. **Idempotency**:
   - Offers: InvestmentIntent.idempotency_key
   - Vaults: Pas d'idempotency key (mais WithdrawalRequest peut servir)

4. **Status**:
   - Offers: InvestmentIntent.status (PENDING/CONFIRMED/REJECTED)
   - Vaults: WithdrawalRequest.status (PENDING/EXECUTED/CANCELLED)

5. **FIFO Queue**:
   - Offers: Pas de queue (allocation immédiate ou reject)
   - Vaults: WithdrawalRequest PENDING → FIFO processing

---

## COMMANDES CURL POUR TEST

### Investir dans une offer

```bash
TOKEN="your_jwt_token"
OFFER_ID="offer_uuid_here"
AMOUNT="1000.00"
IDEMPOTENCY_KEY=$(uuidgen)

curl -X POST "http://localhost:8000/api/v1/offers/${OFFER_ID}/invest" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"amount\": \"${AMOUNT}\",
    \"currency\": \"AED\",
    \"idempotency_key\": \"${IDEMPOTENCY_KEY}\"
  }"
```

### Vérifier le wallet après investissement

```bash
curl -X GET "http://localhost:8000/api/v1/wallet?currency=AED" \
  -H "Authorization: Bearer ${TOKEN}"
```

### Vérifier les transactions

```bash
curl -X GET "http://localhost:8000/api/v1/transactions?limit=10" \
  -H "Authorization: Bearer ${TOKEN}"
```

---

## FICHIERS RÉFÉRENCÉS

### Backend
- `backend/app/api/v1/offers.py` (endpoint)
- `backend/app/services/offers/service_v1_1.py` (logique métier)
- `backend/app/services/fund_services.py` (lock_funds_for_investment)
- `backend/app/core/ledger/models.py` (Operation, LedgerEntry)
- `backend/app/core/accounts/models.py` (Account, AccountType)
- `backend/app/core/offers/models.py` (Offer, InvestmentIntent)

### Frontend
- `frontend-client/app/invest/[id]/page.tsx` (page investissement)
- `frontend-client/lib/api.ts` (API wrapper)
- `frontend-client/components/offers/OfferInvestCard.tsx` (composant UI)

---

**Date**: 2025-01-26
**Version**: 1.0
