# Development Runbook

Guide rapide pour démarrer et maintenir l'environnement de développement.

## Prérequis

- **Docker Desktop** installé et en cours d'exécution
- Ports libres : `3000`, `3001`, `8000`, `5432`, `6379`
- (Optionnel) Node.js si vous voulez développer en local sans Docker

## Démarrage rapide

### Une seule commande

```bash
make dev-up
```

Cette commande :
- Vérifie que Docker est en cours d'exécution
- Crée `.env.dev` depuis `.env.dev.example` si nécessaire
- Démarre tous les services (backend, frontends, postgres, redis)
- Attend que le backend soit sain
- Affiche les URLs d'accès

### URLs après démarrage

- **Frontend Client** : http://localhost:3000
- **Frontend Admin** : http://localhost:3001
- **Backend API** : http://localhost:8000
- **API Docs** : http://localhost:8000/docs

## Commandes d'audit

### Audit runtime complet

```bash
make audit-runtime
```

Vérifie :
- Fichiers de configuration (`.env.dev`, `.gitignore`)
- Variables d'environnement requises
- Services Docker
- Santé de l'API (CORS, endpoints)
- Frontends accessibles

### Audit schéma base de données

```bash
make audit-db
```

Vérifie que le schéma PostgreSQL est à jour avec les migrations Alembic.

### Audit anti-hardcode

```bash
make audit-hardcode
```

Détecte les URLs, endpoints R2/S3, ou secrets hardcodés dans le code.

## Commandes utiles

### Voir les logs

```bash
# Tous les services
docker compose -f docker-compose.dev.yml logs -f

# Backend uniquement
docker compose -f docker-compose.dev.yml logs -f backend

# Frontend-client uniquement
docker compose -f docker-compose.dev.yml logs -f frontend-client
```

### Arrêter les services

```bash
docker compose -f docker-compose.dev.yml down
```

### Redémarrer un service

```bash
docker compose -f docker-compose.dev.yml restart backend
```

### Appliquer les migrations

```bash
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
```

## Troubleshooting

### "Failed to fetch" dans le frontend

**Causes possibles :**
1. Backend non démarré ou crashé
2. CORS mal configuré
3. `NEXT_PUBLIC_API_BASE_URL` manquant ou incorrect

**Solutions :**
```bash
# 1. Vérifier que le backend tourne
docker compose -f docker-compose.dev.yml ps backend

# 2. Vérifier les logs backend
docker compose -f docker-compose.dev.yml logs --tail=50 backend

# 3. Vérifier CORS dans .env.dev
grep CORS_ALLOW_ORIGINS .env.dev

# 4. Vérifier NEXT_PUBLIC_API_BASE_URL dans docker-compose.dev.yml
grep NEXT_PUBLIC_API_BASE_URL docker-compose.dev.yml

# 5. Relancer l'audit
make audit-runtime
```

### "CORS blocked" dans la console

**Causes possibles :**
1. Backend crashé (souvent erreur SQLAlchemy)
2. `CORS_ALLOW_ORIGINS` ne contient pas l'origine du frontend
3. `CORS_ALLOW_CREDENTIALS` non activé

**Solutions :**
```bash
# 1. Vérifier les logs backend pour erreurs SQLAlchemy
docker compose -f docker-compose.dev.yml logs backend | grep -iE "(error|exception|traceback|AmbiguousForeignKeysError)"

# 2. Vérifier CORS configuration
make audit-runtime

# 3. Redémarrer le backend
docker compose -f docker-compose.dev.yml restart backend
```

### "Storage failed" ou erreurs R2/S3

**Causes possibles :**
1. Variables S3_* manquantes dans `.env.dev`
2. Bucket R2 non configuré ou credentials invalides
3. CORS bucket R2 non configuré

**Solutions :**
```bash
# 1. Vérifier les variables storage
grep S3_ .env.dev

# 2. Storage est optionnel - si non configuré, les uploads seront désactivés
# Vérifier le statut storage via l'audit
make audit-runtime

# 3. Si storage est requis, configurer dans .env.dev :
#    S3_BUCKET=vancelian-dev
#    S3_ACCESS_KEY_ID=...
#    S3_SECRET_ACCESS_KEY=...
#    S3_ENDPOINT_URL=https://...r2.cloudflarestorage.com
#    S3_REGION=auto
```

### Backend ne démarre pas

**Causes possibles :**
1. Port 8000 déjà utilisé
2. Erreur de migration Alembic
3. Erreur SQLAlchemy (relations ambiguës)

**Solutions :**
```bash
# 1. Vérifier les logs
docker compose -f docker-compose.dev.yml logs backend

# 2. Vérifier les migrations
docker compose -f docker-compose.dev.yml exec backend alembic current
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head

# 3. Vérifier le schéma DB
make audit-db

# 4. Redémarrer proprement
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d --build backend
```

### Frontend ne compile pas

**Causes possibles :**
1. `NEXT_PUBLIC_API_BASE_URL` manquant (devrait être dans docker-compose.dev.yml)
2. Erreur TypeScript
3. Node modules corrompus

**Solutions :**
```bash
# 1. Vérifier les logs
docker compose -f docker-compose.dev.yml logs frontend-client

# 2. Rebuild
docker compose -f docker-compose.dev.yml up -d --build frontend-client

# 3. Vérifier les variables d'environnement
docker compose -f docker-compose.dev.yml exec frontend-client env | grep NEXT_PUBLIC
```

## Configuration

### Variables d'environnement requises

Voir `docs/ENV_REFERENCE.md` pour la liste complète.

**Minimum pour démarrer :**
- `DATABASE_URL` : URL PostgreSQL
- `REDIS_URL` : URL Redis
- `SECRET_KEY` : Clé secrète (min 32 caractères)
- `NEXT_PUBLIC_API_BASE_URL` : URL backend (dans docker-compose.dev.yml pour frontends)
- `CORS_ALLOW_ORIGINS` : Origines autorisées (comma-separated)

**Optionnel (Storage R2/S3) :**
- `S3_BUCKET`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`
- `S3_ENDPOINT_URL`
- `S3_REGION`

### Fichier `.env.dev`

Le fichier `.env.dev` est :
- **Ignoré par Git** (dans `.gitignore`)
- **Chargé automatiquement** par `docker-compose.dev.yml`
- **Créé depuis `.env.dev.example`** si absent lors de `make dev-up`

## Workflow de développement

1. **Démarrer l'environnement :**
   ```bash
   make dev-up
   ```

2. **Vérifier que tout fonctionne :**
   ```bash
   make audit-runtime
   ```

3. **Développer** (modifications hot-reload automatiques)

4. **Avant de commit :**
   ```bash
   make audit-hardcode  # Vérifier qu'aucun hardcode
   make audit-db        # Vérifier migrations
   ```

5. **Arrêter :**
   ```bash
   docker compose -f docker-compose.dev.yml down
   ```

## Support

En cas de problème persistant :
1. Vérifier les logs : `docker compose -f docker-compose.dev.yml logs`
2. Lancer l'audit complet : `make audit-runtime`
3. Vérifier la documentation : `docs/ENV_REFERENCE.md`

