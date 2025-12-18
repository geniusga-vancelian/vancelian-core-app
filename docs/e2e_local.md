# E2E Local Testing Guide

Guide rapide pour tester le flux complet de dépôt en local.

## Happy Path - Flux de dépôt complet

### 1. Exécuter le flux E2E complet (une seule commande)

```bash
curl -X POST "http://localhost:8000/dev/v1/e2e/deposit-flow" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@vancelian.dev",
    "sub": "11111111-1111-1111-1111-111111111111",
    "currency": "AED",
    "amount": "1000.00",
    "iban": "AE123456789012345678901"
  }' | jq
```

**Réponse attendue :**

```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "subject": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@vancelian.dev",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "provider_event_id": "e2e-abc123...",
  "webhook_submit_status": "success",
  "wallet_balances": {
    "available": "0.00",
    "blocked": "1000.00",
    "locked": "0.00",
    "total": "1000.00"
  },
  "last_transaction": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "status": "COMPLIANCE_REVIEW",
    "created_at": "2025-12-18T10:00:00Z"
  }
}
```

### 2. Vérifier le wallet

```bash
# Utiliser le token retourné
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X GET "http://localhost:8000/api/v1/wallet?currency=AED" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 3. Libérer les fonds (endpoint admin)

```bash
# Utiliser un token admin
ADMIN_TOKEN="..." # Générer via /dev/v1/token/admin

curl -X POST "http://localhost:8000/admin/v1/compliance/release-funds" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "<transaction_id from step 1>",
    "amount": "1000.00",
    "reason": "E2E test - compliance approved"
  }' | jq
```

### 4. Vérifier le wallet après libération

```bash
curl -X GET "http://localhost:8000/api/v1/wallet?currency=AED" \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Résultat attendu :**
- `available`: `1000.00`
- `blocked`: `0.00`
- `total`: `1000.00`

### 5. Tester l'investissement (optionnel)

```bash
# D'abord, créer une offre (admin)
# Puis investir
curl -X POST "http://localhost:8000/api/v1/investments" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "500.00",
    "currency": "AED",
    "offer_id": "<offer_id>",
    "reason": "E2E test investment"
  }' | jq
```

### 6. Voir les transactions

Accéder à la page frontend : `http://localhost:3000/transactions`

## Notes importantes

- **Idempotence** : Si vous réexécutez la même commande avec le même `provider_event_id`, le webhook retournera le statut "duplicate" et la transaction existante.
- **DEV-ONLY** : Tous ces endpoints sont uniquement disponibles quand `DEV_MODE=true`.
- **Token** : Le token généré est valide 7 jours par défaut.
- **Statut transaction** : Après dépôt, le statut est `COMPLIANCE_REVIEW`. Les fonds sont dans `blocked_balance`.

