# Offers API - Debug Guide

Ce document contient des commandes curl pour tester l'endpoint `/api/v1/offers` et vérifier la configuration CORS.

## Prérequis

1. Backend démarré sur `http://localhost:8000`
2. Token d'authentification valide (obtenu via `/api/v1/auth/login` ou `/api/v1/auth/register`)

## Obtenir un token

```bash
# Option 1: Register un nouvel utilisateur
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3000" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!",
    "full_name": "Test User"
  }'

# Option 2: Login avec un utilisateur existant
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3000" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!"
  }'

# Extraire le token de la réponse (exemple avec jq)
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPassword123!"}' | jq -r '.access_token')

echo "Token: $TOKEN"
```

## Tester l'endpoint /api/v1/offers

### 1. Liste des offers LIVE (succès attendu)

```bash
# Avec tous les paramètres (comme le frontend)
curl -i "http://localhost:8000/api/v1/offers?status=LIVE&currency=AED&limit=50&offset=0" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Origin: http://localhost:3000" \
  -H "Content-Type: application/json"

# Vérifier les en-têtes CORS dans la réponse:
# - Access-Control-Allow-Origin: http://localhost:3000
# - Access-Control-Allow-Credentials: true
```

### 2. Liste des offers avec currency par défaut (AED)

```bash
curl -i "http://localhost:8000/api/v1/offers?limit=10" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Origin: http://localhost:3000"
```

### 3. Test avec status invalide (devrait retourner 400)

```bash
curl -i "http://localhost:8000/api/v1/offers?status=INVALID&currency=AED" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Origin: http://localhost:3000"

# Réponse attendue:
# HTTP/1.1 400 Bad Request
# {
#   "error": {
#     "code": "INVALID_STATUS",
#     "message": "Invalid status: 'INVALID'. Only 'LIVE' status is supported for regular users.",
#     "trace_id": "..."
#   }
# }
```

### 4. Test sans token (devrait retourner 401)

```bash
curl -i "http://localhost:8000/api/v1/offers?currency=AED" \
  -H "Origin: http://localhost:3000"

# Réponse attendue:
# HTTP/1.1 401 Unauthorized
# {
#   "error": {
#     "code": "AUTHORIZATION_MISSING",
#     "message": "Authorization header missing",
#     "trace_id": "..."
#   }
# }
```

### 5. Test CORS preflight (OPTIONS)

```bash
curl -i -X OPTIONS "http://localhost:8000/api/v1/offers" \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization,Content-Type"

# Réponse attendue:
# HTTP/1.1 200 OK
# Access-Control-Allow-Origin: http://localhost:3000
# Access-Control-Allow-Methods: *
# Access-Control-Allow-Headers: *
# Access-Control-Allow-Credentials: true
```

## Vérifier les logs backend

Si une erreur 500 se produit, vérifier les logs :

```bash
# Docker logs
docker logs vancelian-backend-dev --tail 100 | grep -A 20 "offers\|error\|exception"

# Ou directement dans le container
docker exec vancelian-backend-dev tail -f /app/logs/*.log
```

## Format des erreurs attendues

Toutes les erreurs doivent retourner un format JSON structuré :

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "trace_id": "uuid-v4-trace-id"
  }
}
```

### Codes d'erreur possibles

- `INVALID_STATUS`: Status invalide (seul "LIVE" est accepté)
- `AUTHORIZATION_MISSING`: Token manquant
- `TOKEN_EXPIRED`: Token expiré
- `INTERNAL_ERROR`: Erreur serveur (500) - vérifier les logs avec le trace_id

## Vérification CORS

Pour vérifier que CORS fonctionne correctement :

1. **Avec Origin header** : Les en-têtes CORS doivent être présents
2. **Sans Origin header** : Les en-têtes CORS peuvent être absents (comportement normal)
3. **Sur les erreurs** : Les en-têtes CORS doivent être présents même sur les erreurs 400/500

### Test rapide CORS

```bash
# Test avec Origin
curl -i "http://localhost:8000/api/v1/offers?currency=AED" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Origin: http://localhost:3000" \
  | grep -i "access-control"

# Devrait afficher:
# access-control-allow-origin: http://localhost:3000
# access-control-allow-credentials: true
```

## Dépannage

### Erreur 500 sur /api/v1/offers

1. Vérifier les logs backend pour le traceback complet
2. Vérifier que la table `offers` existe et contient des colonnes attendues
3. Vérifier que `OfferStatus.LIVE` est bien défini dans le modèle
4. Vérifier que les relations (media, documents) ne causent pas d'erreurs

### Erreur CORS "No Access-Control-Allow-Origin"

1. Vérifier que `CORS_ENABLED=true` dans `docker-compose.dev.yml`
2. Vérifier que `CORS_ALLOW_ORIGINS` contient `http://localhost:3000`
3. Vérifier que l'en-tête `Origin: http://localhost:3000` est envoyé dans la requête
4. Redémarrer le backend après modification de la configuration CORS

### Erreur 401 "Authorization header missing"

1. Vérifier que le token est inclus dans l'en-tête : `Authorization: Bearer $TOKEN`
2. Vérifier que le token n'est pas expiré
3. Vérifier que le token est valide (obtenu via login/register)

## Notes

- Le paramètre `status` est optionnel et accepte uniquement "LIVE" (pour backward compatibility)
- Si `status` n'est pas fourni, l'endpoint filtre automatiquement pour `OfferStatus.LIVE`
- Le paramètre `currency` par défaut est "AED" si non spécifié
- Toutes les erreurs incluent un `trace_id` pour faciliter le debugging

