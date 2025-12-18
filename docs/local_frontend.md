# Guide de développement Frontend (Next.js)

## Configuration de l'environnement

### Variables d'environnement

Créer un fichier `frontend/.env.local` avec:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_ZAND_WEBHOOK_SECRET=dev_secret_placeholder
```

**⚠️ Important**: 
- Les variables `NEXT_PUBLIC_*` sont exposées au navigateur (elles sont compilées dans le bundle JavaScript).
- Ne jamais y mettre de secrets de production.
- Ne jamais commiter `.env.local` dans Git.

### Base URL de l'API

Le frontend utilise `NEXT_PUBLIC_API_BASE_URL` pour toutes les requêtes API. Par défaut, si non défini, il utilise `http://localhost:8000`.

Le code utilise `process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'` (nullish coalescing).

## Démarrage du frontend en développement

```bash
cd frontend
npm install  # ou yarn install / pnpm install
npm run dev  # ou yarn dev / pnpm dev
```

Le frontend sera disponible sur http://localhost:3000

## Communication Frontend ↔ Backend

### Depuis le navigateur (browser)

Toutes les requêtes depuis le navigateur utilisent l'URL complète: `${NEXT_PUBLIC_API_BASE_URL}${endpoint}`

Exemple: `http://localhost:8000/api/v1/wallet`

### Configuration CORS

Le backend doit autoriser l'origine du frontend dans `CORS_ALLOW_ORIGINS`:

- `http://localhost:3000` (localhost standard)
- `http://127.0.0.1:3000` (localhost alternatif)

Ces origines sont configurées par défaut dans `docker-compose.dev.yml`:

```yaml
CORS_ENABLED: "true"
CORS_ALLOW_ORIGINS: http://localhost:3000,http://127.0.0.1:3000
```

## CORS et requêtes préliminaires (Preflight)

### Pourquoi les requêtes préliminaires (OPTIONS) sont nécessaires

Quand le navigateur envoie une requête avec des en-têtes personnalisés (comme `Authorization`), il effectue d'abord une requête **OPTIONS** (appelée "preflight") pour vérifier si le serveur autorise cette requête.

**Important** : Les requêtes avec l'en-tête `Authorization` déclenchent toujours une requête préliminaire OPTIONS.

### Configuration CORS requise

Pour que les requêtes depuis le navigateur fonctionnent, le backend doit :
1. Autoriser l'origine `http://localhost:3000` (ou `http://127.0.0.1:3000`)
2. Autoriser la méthode HTTP utilisée (GET, POST, etc.)
3. Autoriser l'en-tête `Authorization`
4. Répondre correctement aux requêtes OPTIONS (preflight)

### Origines et en-têtes autorisés

**Origines autorisées (défaut)** :
- `http://localhost:3000`
- `http://127.0.0.1:3000`

**En-têtes autorisés (défaut)** :
- `Authorization` (requis pour l'authentification)
- `Content-Type`
- `Idempotency-Key`
- `X-Request-Id`
- `Accept`
- `Origin`

**Méthodes autorisées** :
- GET, POST, PUT, PATCH, DELETE, OPTIONS

### CORS pour les webhooks en DEV

Pour permettre au simulateur ZAND Webhook (frontend) d'appeler le backend en DEV depuis `http://localhost:3000`, 
le backend autorise les en-têtes webhooks suivants via CORS :

- `X-Zand-Signature` / `X-Zand-Timestamp` (ou `X-Webhook-*` équivalents)
- `Content-Type`
- `Authorization`, `Idempotency-Key`, `X-Request-Id`, etc.

**Important** : Ces en-têtes sont autorisés uniquement au niveau CORS (preflight OPTIONS). 
Les requêtes POST `/webhooks/v1/*` restent **protégées par la vérification HMAC** en production.

**Rebuild backend après modification CORS :**

```bash
docker-compose -f docker-compose.dev.yml up -d --build backend
```

**Tester le preflight (DEV) :**

```bash
curl -i -X OPTIONS \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: X-Zand-Signature,X-Zand-Timestamp,Content-Type" \
  http://localhost:8000/webhooks/v1/zand/deposit
```

Vous devez voir un HTTP **200/204** avec des en-têtes `Access-Control-*` corrects incluant `X-Zand-Signature` et `X-Zand-Timestamp` dans `Access-Control-Allow-Headers`.

### Dépannage des erreurs de webhook

Si le webhook échoue avec une erreur de signature ou de vérification :

1. **Erreurs HMAC/Signature** : Le backend retourne des codes d'erreur spécifiques :
   - `WEBHOOK_MISSING_HEADER` : En-tête manquant (X-Zand-Signature)
   - `WEBHOOK_INVALID_SIGNATURE` : Signature HMAC invalide
   - `WEBHOOK_INVALID_TIMESTAMP` : Format de timestamp invalide
   - `WEBHOOK_TIMESTAMP_SKEW` : Timestamp trop ancien/nouveau
   - `WEBHOOK_INVALID_BODY` : Format JSON invalide

2. **Utiliser l'endpoint de signature DEV** : Pour éliminer les erreurs de signature, utilisez l'endpoint DEV qui génère exactement la requête signée correcte :
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
   
   Cet endpoint retourne :
   - `payload` : Le JSON exact à envoyer
   - `headers` : Les en-têtes avec signature et timestamp calculés
   - `curl_example` : Une commande curl prête à l'emploi
   
   **Note** : Cet endpoint utilise le MÊME secret et algorithme que la vérification de production, garantissant que la signature générée sera toujours valide.

3. **Vérifier les logs du backend** : Les logs incluent maintenant des détails structurés :
   - `trace_id` : Pour tracer la requête
   - `error_code` : Code d'erreur spécifique
   - `signature_preview` : Aperçu de la signature (premiers 8 caractères)
   - `body_length` : Longueur du body en bytes

## Si vous voyez "Failed to fetch"

Cette erreur indique généralement un problème de connexion réseau ou CORS entre le frontend et le backend.

### Vérifications rapides

1. **Backend est-il en cours d'exécution ?**
   ```bash
   curl http://localhost:8000/health
   ```
   Devrait retourner `200 OK`.

2. **Swagger est-il accessible ?**
   ```bash
   # Ouvrir dans le navigateur
   http://localhost:8000/docs
   ```
   Si Swagger ne se charge pas, le backend n'est pas accessible.

3. **Vérifier les logs du backend pour les erreurs CORS**
   ```bash
   docker-compose -f docker-compose.dev.yml logs backend | grep -i cors
   ```
   Ou vérifier les logs complets:
   ```bash
   docker-compose -f docker-compose.dev.yml logs -f backend
   ```

4. **Vérifier la configuration CORS dans le backend**
   - Ouvrir les DevTools du navigateur (F12)
   - Onglet "Network"
   - Chercher la requête qui échoue
   - Vérifier les en-têtes de réponse:
     - `Access-Control-Allow-Origin` doit contenir `http://localhost:3000` ou `*`
     - Si la requête est OPTIONS (preflight), vérifier que `Access-Control-Allow-Methods` inclut la méthode utilisée

5. **Confirmer NEXT_PUBLIC_API_BASE_URL**
   - Dans la console du navigateur (DevTools), exécuter:
     ```javascript
     console.log(process.env.NEXT_PUBLIC_API_BASE_URL)
     ```
   - Devrait afficher `http://localhost:8000` (ou votre valeur personnalisée)
   - Si `undefined`, vérifier que `.env.local` existe et contient `NEXT_PUBLIC_API_BASE_URL`

6. **Vérifier que les deux services sont sur les bons ports**
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000

### Solutions courantes

#### 1. Backend non démarré
```bash
docker-compose -f docker-compose.dev.yml up -d --build
```

#### 2. CORS mal configuré
Vérifier que `docker-compose.dev.yml` contient:
```yaml
backend:
  environment:
    CORS_ENABLED: "true"
    CORS_ALLOW_ORIGINS: http://localhost:3000,http://127.0.0.1:3000
```

Puis redémarrer le backend:
```bash
docker-compose -f docker-compose.dev.yml restart backend
```

#### 3. Variable d'environnement manquante
Créer `frontend/.env.local`:
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Puis redémarrer le serveur Next.js:
```bash
# Arrêter (Ctrl+C) et relancer
npm run dev
```

#### 4. Cache du navigateur
- Hard refresh: `Ctrl+Shift+R` (Windows/Linux) ou `Cmd+Shift+R` (Mac)
- Ou vider le cache du navigateur

#### 5. Port déjà utilisé
Vérifier qu'aucun autre service n'utilise le port 8000:
```bash
# macOS/Linux
lsof -i :8000

# Windows
netstat -ano | findstr :8000
```

## Messages d'erreur améliorés

Le frontend affiche maintenant des messages d'erreur détaillés incluant:
- Code d'erreur HTTP (ex: `HTTP_404`, `HTTP_500`)
- Message d'erreur du backend
- Trace ID (pour déboguer côté backend)
- Détails additionnels si disponibles

En cas d'erreur réseau (type "Failed to fetch"), un message spécifique explique les causes possibles (CORS, backend down, etc.).

## Structure des erreurs API

Toutes les erreurs API suivent le format standard:

```typescript
{
  error: {
    code: string        // Ex: "HTTP_404", "VALIDATION_ERROR", "NETWORK_ERROR"
    message: string     // Message lisible
    details?: any       // Détails additionnels (optionnel)
    trace_id?: string   // ID de trace pour le débogage (optionnel)
  }
}
```

Le frontend affiche ces informations dans l'interface utilisateur en cas d'erreur.

## Débogage avancé

### Voir les requêtes réseau dans le navigateur

1. Ouvrir les DevTools (F12)
2. Onglet "Network"
3. Filtrer par "Fetch/XHR"
4. Inspecter chaque requête:
   - Status code
   - Headers (Request et Response)
   - Payload (Request et Response)

### Vérifier les logs du backend

```bash
# Logs en temps réel
docker-compose -f docker-compose.dev.yml logs -f backend

# Chercher les requêtes CORS/preflight
docker-compose -f docker-compose.dev.yml logs backend | grep -i "OPTIONS\|CORS\|preflight"
```

### Tester l'API directement depuis le terminal

```bash
# Test health
curl http://localhost:8000/health

# Test avec authentification (remplacer TOKEN par un JWT valide)
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/v1/wallet
```

## Génération de tokens JWT et bootstrap utilisateur (DEV-ONLY)

### Activer le mode DEV

Les endpoints DEV (`/dev/v1/*`) ne sont disponibles que si `DEV_MODE=true` dans les variables d'environnement du backend.

Dans `docker-compose.dev.yml`, cette variable est déjà configurée :
```yaml
DEV_MODE: "true"
```

Si les endpoints retournent 404, vérifiez que `DEV_MODE=true` est bien défini.

### Bootstrap d'un utilisateur de test

Pour créer un utilisateur de test avec ses comptes wallet par défaut (nécessaire pour utiliser le simulateur de webhook ZAND) :

```bash
curl -X POST "http://localhost:8000/dev/v1/bootstrap/user" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@vancelian.dev",
    "sub": "11111111-1111-1111-1111-111111111111",
    "currency": "AED"
  }' | jq
```

**Options (toutes optionnelles avec valeurs par défaut) :**
- `email` (défaut: `"user@vancelian.dev"`) : Email de l'utilisateur
- `sub` (défaut: `"11111111-1111-1111-1111-111111111111"`) : Subject (external_subject) pour OIDC
- `currency` (défaut: `"AED"`) : Devise pour créer les comptes wallet

**Réponse :**
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

**Comportement idempotent :** Si l'utilisateur existe déjà (par email ou external_subject), l'endpoint retourne l'utilisateur existant et ses comptes.

**Comptes créés :**
- `WALLET_AVAILABLE` : Fonds disponibles pour les opérations utilisateur
- `WALLET_BLOCKED` : Fonds bloqués (en attente de review compliance)
- `WALLET_LOCKED` : Fonds verrouillés (pour investissements)

### Générer un token admin

Pour générer un token JWT avec les rôles ADMIN et COMPLIANCE (utile pour tester les endpoints admin) :

```bash
curl -X POST "http://localhost:8000/dev/v1/token/admin?expires_in_days=7" | jq
```

Réponse :
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 604800,
  "subject": "550e8400-e29b-41d4-a716-446655440000",
  "email": "admin@vancelian.dev",
  "roles": ["ADMIN", "COMPLIANCE"]
}
```

**Options :**
- `subject` (optionnel) : UUID personnalisé pour le claim `sub`. Si non fourni, un UUID aléatoire est généré.
- `expires_in_days` (optionnel, défaut: 7) : Durée de validité du token en jours (1-30).

**Exemples :**

```bash
# Token avec UUID personnalisé
curl -X POST "http://localhost:8000/dev/v1/token/admin?subject=11111111-1111-1111-1111-111111111111"

# Token valide 1 jour
curl -X POST "http://localhost:8000/dev/v1/token/admin?expires_in_days=1"

# Extraire uniquement le token
curl -s -X POST "http://localhost:8000/dev/v1/token/admin" | jq -r '.access_token'
```

**⚠️ Important :**
- Cet endpoint est **UNIQUEMENT** disponible quand `DEV_MODE=true`
- Ne jamais exposer cet endpoint en production
- Le token est signé avec `JWT_SECRET` configuré dans `docker-compose.dev.yml`

### Générer un token USER

Pour générer un token JWT avec le rôle USER (pour tester les endpoints utilisateur) :

```bash
curl -X POST "http://localhost:8000/dev/v1/token/user?subject=11111111-1111-1111-1111-111111111111&email=user@vancelian.dev&expires_in_days=7" | jq
```

**Options :**
- `subject` (optionnel, défaut: `"11111111-1111-1111-1111-111111111111"`) : UUID pour le claim `sub`
- `email` (optionnel, défaut: `"user@vancelian.dev"`) : Email pour le claim `email`
- `expires_in_days` (optionnel, défaut: 7) : Durée de validité en jours (1-30)

**Réponse :**
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

### Workflow complet pour tester le simulateur ZAND Webhook

1. **Activer DEV_MODE** (déjà fait dans `docker-compose.dev.yml`) :
   ```yaml
   DEV_MODE: "true"
   ```

2. **Bootstrap utilisateur** :
   ```bash
   curl -X POST "http://localhost:8000/dev/v1/bootstrap/user" | jq
   ```
   Copier le `user_id` retourné.

3. **Utiliser le `user_id` dans le simulateur ZAND Webhook** :
   - Aller sur `http://localhost:3000/tools/zand-webhook`
   - Coller le `user_id` dans le champ "User ID (UUID)"

4. **Générer un token USER** :
   ```bash
   curl -s -X POST "http://localhost:8000/dev/v1/token/user" | jq -r '.access_token'
   ```
   Coller le token dans le champ "JWT Token" du frontend.

5. **Tester le webhook** :
   - Remplir les champs du simulateur
   - Cliquer sur "Send Webhook"
   - Vérifier que le dépôt arrive dans `WALLET_BLOCKED` (en attente de review compliance)

