# E2E Test Path - Guide Rapide

Guide étape par étape pour tester le flux complet de dépôt en local.

## Prérequis

- Backend en cours d'exécution sur `http://localhost:8000`
- Frontend en cours d'exécution sur `http://localhost:3000`
- `DEV_MODE=true` dans `docker-compose.dev.yml`

Vérifier que le backend répond :

```bash
curl http://localhost:8000/health
```

---

## Step A: Bootstrap User

Crée ou récupère un utilisateur de test avec ses comptes wallet par défaut.

```bash
curl -X POST "http://localhost:8000/dev/v1/bootstrap/user" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@vancelian.dev",
    "sub": "11111111-1111-1111-1111-111111111111",
    "currency": "AED"
  }' | jq
```

**Réponse attendue :**

```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@vancelian.dev",
  "currency": "AED",
  "accounts": {
    "available_account_id": "660e8400-e29b-41d4-a716-446655440001",
    "blocked_account_id": "770e8400-e29b-41d4-a716-446655440002",
    "locked_account_id": "880e8400-e29b-41d4-a716-446655440003"
  }
}
```

**Important :** Notez le `user_id` retourné (vous pouvez aussi utiliser le `sub` directement).

---

## Step B: Generate USER Token

Génère un token JWT avec le rôle USER pour authentifier les requêtes API.

```bash
curl -X POST "http://localhost:8000/dev/v1/token/user?subject=11111111-1111-1111-1111-111111111111&email=user@vancelian.dev" | jq
```

**Réponse attendue :**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 604800,
  "subject": "11111111-1111-1111-1111-111111111111",
  "email": "user@vancelian.dev",
  "roles": ["USER"]
}
```

**Important :** Copiez le `access_token` pour l'étape suivante.

---

## Step C: Paste Token into Frontend

1. Ouvrir le frontend : `http://localhost:3000`
2. Trouver le composant **TokenBar** en haut de la page
3. Coller le `access_token` dans le champ "JWT Token"
4. Le token est automatiquement décodé et les claims affichés

**Vérification :** Vous devriez voir :
- `sub: 11111111-1111-1111-1111-111111111111`
- `email: user@vancelian.dev`
- `roles: USER`

---

## Step D: Send ZAND Webhook from Frontend Simulator

1. Aller sur `http://localhost:3000/tools/zand-webhook`
2. Le champ **"User (sub)"** est automatiquement rempli avec le `sub` du JWT
3. Vérifier que **"Use backend signer (recommended)"** est coché (par défaut)
4. Remplir les autres champs :
   - **Provider Event ID** : Générer un UUID (bouton "Generate UUID") ou utiliser un ID unique
   - **IBAN** : `AE123456789012345678901` (défaut)
   - **Amount** : `1000.00`
   - **Currency** : `AED` (défaut)
   - **Occurred At** : Date/heure actuelle (défaut)
5. Cliquer sur **"Send Webhook"**

**Résultat attendu :**

- ✅ Succès : Message vert avec `transaction_id` et `status: accepted`
- Le webhook est traité et la transaction créée avec le statut `COMPLIANCE_REVIEW`

---

## Step E: Verify Results

### E.1: Check Wallet Balance

Depuis le frontend (`http://localhost:3000/wallet`) ou via API :

```bash
# Utiliser le token de Step B
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X GET "http://localhost:8000/api/v1/wallet?currency=AED" \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Résultat attendu après dépôt :**

```json
{
  "currency": "AED",
  "total_balance": "1000.00",
  "available_balance": "0.00",
  "blocked_balance": "1000.00",
  "locked_balance": "0.00"
}
```

**Explication :**
- `total_balance`: `1000.00` (fonds totaux)
- `blocked_balance`: `1000.00` (fonds bloqués en attente de review compliance)
- `available_balance`: `0.00` (fonds non disponibles tant que compliance n'a pas approuvé)

### E.2: Check Transactions

Aller sur `http://localhost:3000/transactions`

Vous devriez voir :
- **Transaction ID** : UUID de la transaction créée
- **Type** : `DEPOSIT`
- **Status** : `COMPLIANCE_REVIEW`
- **Amount** : `1000.00 AED`
- **Created At** : Date/heure du dépôt

---

## If It Fails

### 401 Invalid Token

**Symptôme :** `401 Unauthorized` ou `Token invalid`

**Causes possibles :**
- `JWT_SECRET` ne correspond pas entre backend et token
- Backend reconstruit sans redémarrer complètement

**Solution :**
```bash
# Rebuild et redémarrer backend
docker-compose -f docker-compose.dev.yml up -d --build backend

# Régénérer le token après rebuild
curl -X POST "http://localhost:8000/dev/v1/token/user?subject=11111111-1111-1111-1111-111111111111&email=user@vancelian.dev" | jq
```

### CORS Preflight Fails

**Symptôme :** `Failed to fetch` ou erreur CORS dans la console du navigateur

**Causes possibles :**
- En-têtes webhooks manquants dans `CORS_ALLOW_HEADERS`

**Solution :**
Vérifier que `backend/app/infrastructure/settings.py` inclut :
- `X-Zand-Signature`
- `X-Zand-Timestamp`
- `X-Webhook-Signature`
- `X-Webhook-Timestamp`

Puis rebuild backend :
```bash
docker-compose -f docker-compose.dev.yml up -d --build backend
```

### 500 Webhook Error / Signature Mismatch

**Symptôme :** Webhook retourne `500` ou `WEBHOOK_INVALID_SIGNATURE`

**Causes possibles :**
- Signature HMAC calculée différemment entre frontend et backend
- Secret webhook non configuré ou différent

**Solution :**
Utiliser l'endpoint backend signer pour générer la signature correcte :

1. **Option 1 : Utiliser le toggle "Use backend signer" dans le simulateur frontend**
   - Le simulateur appelle automatiquement `/dev/v1/webhooks/zand/deposit/sign`
   - Affiche le payload + headers signés avant envoi

2. **Option 2 : Générer manuellement la signature backend**

```bash
curl -X POST "http://localhost:8000/dev/v1/webhooks/zand/deposit/sign" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_event_id": "test-123",
    "iban": "AE123456789012345678901",
    "user_sub": "11111111-1111-1111-1111-111111111111",
    "amount": "1000.00",
    "currency": "AED"
  }' | jq
```

Utiliser les `headers` et `payload` retournés pour envoyer le webhook.

---

## Alternative: One-Command E2E Flow

Pour tester le flux complet en une seule commande (bootstrap + token + webhook + balances) :

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

Cette commande retourne directement :
- `user_id`, `token`, `provider_event_id`
- `webhook_submit_status`
- `wallet_balances` (available, blocked, locked, total)
- `last_transaction` (id, status, created_at)

Voir `docs/e2e_local.md` pour plus de détails.

