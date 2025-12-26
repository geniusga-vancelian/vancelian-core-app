# TEST SYSTEM WALLETS — COMMANDES

## ✅ 1. Tests Pytest (PASSÉS)

Tous les 7 tests passent:
```bash
docker-compose exec backend pytest tests/test_system_wallets.py -v
```

**Résultats**: ✅ 7 passed

---

## 2. Tester les Helpers (via script Python)

Les helpers fonctionnent correctement (testés via pytest). Pour tester manuellement:

```python
from app.services.system_wallet_helpers import (
    ensure_offer_system_wallet,
    ensure_vault_system_wallet,
    get_offer_system_wallet_balances,
    get_vault_system_wallet_balances
)

# Pour un offer
wallet = ensure_offer_system_wallet(db, offer_id, "AED")
balances = get_offer_system_wallet_balances(db, offer_id, "AED")

# Pour un vault
wallet = ensure_vault_system_wallet(db, vault_id, "AED")
balances = get_vault_system_wallet_balances(db, vault_id, "AED")
```

---

## 3. Tester les Endpoints Admin API

### Étape 1: Obtenir un token admin

```bash
# Login admin
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "admin@example.com",
    "password": "your_password"
  }'

# Récupérer le token depuis la réponse: {"access_token": "..."}
export TOKEN="votre_token_ici"
```

### Étape 2: Obtenir l'ID d'une offer existante

```bash
# Lister les offers
curl -X GET "http://localhost:8000/api/v1/admin/offers" \
  -H "Authorization: Bearer ${TOKEN}" | jq '.[0].id'

# Ou utiliser directement un ID connu
export OFFER_ID="votre_offer_id"
```

### Étape 3: Tester GET /api/v1/admin/offers/{offer_id}/system-wallet

```bash
curl -X GET "http://localhost:8000/api/v1/admin/offers/${OFFER_ID}/system-wallet" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" | jq
```

**Response attendue**:
```json
{
  "scope_type": "OFFER",
  "scope_id": "123e4567-e89b-12d3-a456-426614174000",
  "currency": "AED",
  "available": "0.00",
  "locked": "0.00",
  "blocked": "0.00"
}
```

### Étape 4: Tester GET /api/v1/admin/vaults/{vault_code}/system-wallet

```bash
# Tester avec FLEX (ou autre vault existant)
curl -X GET "http://localhost:8000/api/v1/admin/vaults/FLEX/system-wallet" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" | jq
```

**Response attendue**:
```json
{
  "scope_type": "VAULT",
  "scope_id": "123e4567-e89b-12d3-a456-426614174001",
  "currency": "AED",
  "available": "0.00",  // Depuis VAULT_POOL_CASH
  "locked": "0.00",
  "blocked": "0.00"
}
```

---

## 4. Script de test complet

```bash
#!/bin/bash
# test_system_wallets_api.sh

TOKEN="${TOKEN:-your_token_here}"
BASE_URL="http://localhost:8000"

echo "Testing System Wallets API..."
echo ""

# Test 1: Offer system wallet
echo "1. Testing GET /api/v1/admin/offers/{id}/system-wallet"
OFFER_ID=$(curl -s -X GET "${BASE_URL}/api/v1/admin/offers" \
  -H "Authorization: Bearer ${TOKEN}" | jq -r '.[0].id // empty')

if [ -n "$OFFER_ID" ]; then
  echo "   Using offer ID: $OFFER_ID"
  curl -s -X GET "${BASE_URL}/api/v1/admin/offers/${OFFER_ID}/system-wallet" \
    -H "Authorization: Bearer ${TOKEN}" | jq
  echo ""
else
  echo "   ⚠️  No offers found"
fi

# Test 2: Vault system wallet
echo "2. Testing GET /api/v1/admin/vaults/FLEX/system-wallet"
curl -s -X GET "${BASE_URL}/api/v1/admin/vaults/FLEX/system-wallet" \
  -H "Authorization: Bearer ${TOKEN}" | jq

echo ""
echo "✅ API tests complete!"
```

---

## RÉSUMÉ DES TESTS

| Test | Status | Méthode |
|------|--------|---------|
| Pytest unit tests | ✅ PASSED (7/7) | `pytest tests/test_system_wallets.py` |
| Helpers (ensure_offer_system_wallet) | ✅ TESTÉ | Via pytest |
| Helpers (ensure_vault_system_wallet) | ✅ TESTÉ | Via pytest |
| API GET /offers/{id}/system-wallet | ⏳ À TESTER | curl (voir ci-dessus) |
| API GET /vaults/{code}/system-wallet | ⏳ À TESTER | curl (voir ci-dessus) |

---

## VÉRIFICATIONS MANUELLES

1. ✅ Migration appliquée: `add_system_wallets_20250126`
2. ✅ Tests pytest: 7/7 passed
3. ⏳ API endpoints: À tester avec curl (voir commandes ci-dessus)
