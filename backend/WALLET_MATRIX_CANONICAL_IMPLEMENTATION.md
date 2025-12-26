# Wallet Matrix - Implémentation Canonique

**Date:** 2025-01-26  
**Version:** v2  
**Endpoint:** `GET /api/v1/dev/wallet-matrix`

---

## Objectif

L'endpoint Wallet Matrix fournit une vue agrégée des balances wallet par instrument (AED, Offers, Vaults) et par état (AVAILABLE, LOCKED, BLOCKED), conforme au canon métier.

---

## Règles d'Agrégation Canoniques

### A) Ligne AED (USER) - Toujours présente

- **Label:** `"AED (USER)"`
- **row_kind:** `"USER_AED"`
- **available:** Balance `WALLET_AVAILABLE` du user (AED)
- **blocked:** Balance `WALLET_BLOCKED` du user (AED)
- **locked:** `"0.00"` (toujours)

**Important:** Ne pas utiliser `WALLET_LOCKED` pour la ligne AED, même si elle est non nulle dans la DB. Les montants "locked" doivent être reclassés sous les instruments (Offer/Vault).

### B) Lignes OFFERS (dynamiques, seulement si le user a investi)

- **Label:** `"OFFRE — <offer_name>"` (fallback: `offer_id`)
- **row_kind:** `"OFFER_USER"`
- **locked:** Exposition investie sur cette offer
- **available:** `"0.00"`
- **blocked:** `"0.00"`

**Source de vérité:**
- Table `investment_intents` avec `status = CONFIRMED`
- `SUM(allocated_amount) WHERE user_id = current_user AND offer_id = offer_id AND status = CONFIRMED`

**Règle:** Ne pas afficher d'offers non investies (pas de ligne si `allocated_amount = 0`).

### C) Lignes VAULTS (dynamiques, seulement si le user a une position)

- **Label:** `"COFFRE — <vault_code>"`
- **row_kind:** `"VAULT_USER"`
- **Source de vérité:** `vault_accounts.principal > 0`

**Règles d'affichage métier:**
- **COFFRE — FLEX:**
  - `available = position_principal`
  - `locked = "0.00"`
  - `blocked = "0.00"`
- **COFFRE — AVENIR:**
  - `available = "0.00"`
  - `locked = position_principal` (vesting)
  - `blocked = "0.00"`

### D) Lignes SYSTEM (optionnel, via query param)

**Query param:** `show_system: bool = false` (par défaut)

Si `show_system=true`:
- Ajoute des lignes système en fin de tableau:
  - `"OFFRE — <name> (SYSTEM)"`: balances offer system wallet
  - `"COFFRE — <code> (SYSTEM)"`: balances vault system wallet
- **row_kind:** `"OFFER_SYSTEM"` ou `"VAULT_SYSTEM"`

---

## Format de Réponse

```json
{
  "currency": "AED",
  "columns": ["available", "locked", "blocked"],
  "rows": [
    {
      "label": "AED (USER)",
      "row_kind": "USER_AED",
      "scope": {
        "type": "USER",
        "id": null,
        "owner": "USER"
      },
      "available": "10000.00",
      "locked": "0.00",
      "blocked": "500.00",
      "meta": {},
      "offer_id": null,
      "vault_id": null,
      "position_principal": null
    },
    {
      "label": "OFFRE — Test Offer Investment",
      "row_kind": "OFFER_USER",
      "scope": {
        "type": "OFFER",
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "owner": "USER"
      },
      "available": "0.00",
      "locked": "5000.00",
      "blocked": "0.00",
      "meta": {
        "offer_code": "TEST-OFFER",
        "offer_name": "Test Offer Investment"
      },
      "offer_id": "123e4567-e89b-12d3-a456-426614174000",
      "vault_id": null,
      "position_principal": "5000.00"
    },
    {
      "label": "COFFRE — FLEX",
      "row_kind": "VAULT_USER",
      "scope": {
        "type": "VAULT",
        "id": "123e4567-e89b-12d3-a456-426614174001",
        "owner": "USER"
      },
      "available": "10000.00",
      "locked": "0.00",
      "blocked": "0.00",
      "meta": {
        "vault_code": "FLEX"
      },
      "offer_id": null,
      "vault_id": "123e4567-e89b-12d3-a456-426614174001",
      "position_principal": "10000.00"
    },
    {
      "label": "COFFRE — AVENIR",
      "row_kind": "VAULT_USER",
      "scope": {
        "type": "VAULT",
        "id": "123e4567-e89b-12d3-a456-426614174002",
        "owner": "USER"
      },
      "available": "0.00",
      "locked": "20000.00",
      "blocked": "0.00",
      "meta": {
        "vault_code": "AVENIR"
      },
      "offer_id": null,
      "vault_id": "123e4567-e89b-12d3-a456-426614174002",
      "position_principal": "20000.00"
    }
  ],
  "meta": {
    "generated_at": "2025-01-26T10:00:00Z",
    "sim_version": "v2",
    "user_id": "123e4567-e89b-12d3-a456-426614174003"
  }
}
```

---

## Format des Montants

- **Toujours des strings** (pas de float)
- **Quantized à 2 décimales** (`"0.00"` format)
- Utilisation de `Decimal.quantize(Decimal('0.01'))`

---

## Exemples cURL

### 1. Requête de base (user exposure seulement)

```bash
curl -X GET "http://localhost:8000/api/v1/dev/wallet-matrix" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json"
```

### 2. Avec système wallets (`show_system=true`)

```bash
curl -X GET "http://localhost:8000/api/v1/dev/wallet-matrix?show_system=true" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json"
```

### 3. Avec currency spécifique (par défaut: AED)

```bash
curl -X GET "http://localhost:8000/api/v1/dev/wallet-matrix?currency=AED" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json"
```

---

## DEV Gate

L'endpoint est **DEV-only** (gated by `settings.debug`).

- Si `debug=false` et `ENV != dev/local`: retourne `403 Forbidden`
- Si `debug=true` ou `ENV in (dev, local, development)`: endpoint accessible

---

## Checklist de Test Manuelle

### Test 1: User sans exposure
- [ ] Appeler `/api/v1/dev/wallet-matrix`
- [ ] Vérifier que `rows` contient seulement `AED (USER)`
- [ ] Vérifier que `locked = "0.00"` pour AED

### Test 2: Après invest offer
- [ ] Créer un `InvestmentIntent` avec `status = CONFIRMED`
- [ ] Appeler `/api/v1/dev/wallet-matrix`
- [ ] Vérifier qu'une ligne `OFFRE — <name>` apparaît avec `row_kind = "OFFER_USER"`
- [ ] Vérifier que `locked > 0` et `available = "0.00"`

### Test 3: Après subscribe vault FLEX
- [ ] Créer un `VaultAccount` avec `vault.code = "FLEX"` et `principal > 0`
- [ ] Appeler `/api/v1/dev/wallet-matrix`
- [ ] Vérifier qu'une ligne `COFFRE — FLEX` apparaît avec `row_kind = "VAULT_USER"`
- [ ] Vérifier que `available = position_principal` et `locked = "0.00"`

### Test 4: Après subscribe vault AVENIR
- [ ] Créer un `VaultAccount` avec `vault.code = "AVENIR"` et `principal > 0`
- [ ] Appeler `/api/v1/dev/wallet-matrix`
- [ ] Vérifier qu'une ligne `COFFRE — AVENIR` apparaît avec `row_kind = "VAULT_USER"`
- [ ] Vérifier que `locked = position_principal` et `available = "0.00"`

### Test 5: System wallets (`show_system=true`)
- [ ] Appeler `/api/v1/dev/wallet-matrix?show_system=true`
- [ ] Vérifier que des lignes `(SYSTEM)` apparaissent en fin de tableau
- [ ] Vérifier que `row_kind` est `"OFFER_SYSTEM"` ou `"VAULT_SYSTEM"`

---

## Fichiers Modifiés

1. ✅ `backend/app/api/v1/dev.py` - Endpoint principal
2. ✅ `backend/tests/test_dev_wallet_matrix.py` - Tests mis à jour

---

## Changements par rapport à v1

- ✅ Ajout de `row_kind` dans chaque row
- ✅ Labels corrigés: `"OFFRE — <name>"` et `"COFFRE — <code>"`
- ✅ Montants quantized à `"0.00"` format (strings)
- ✅ `sim_version` mis à jour à `"v2"`
- ✅ Support `show_system` query param pour les wallets système

---

## Notes Techniques

- **Source de vérité pour Offers:** `InvestmentIntent` avec `status = CONFIRMED`
- **Source de vérité pour Vaults:** `VaultAccount.principal`
- **Mapping FLEX/AVENIR:** FLEX → `available`, AVENIR → `locked`
- **AED locked:** Toujours `"0.00"`, même si `WALLET_LOCKED` est non nul

