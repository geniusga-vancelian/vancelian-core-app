# Cleanup Plan - Mega Clean Baseline

## Plan des changements

### 1. Docker/Compose hygiene
- ✅ Changer ENV default de "development" à "local" dans docker-compose
- ✅ Ajouter commentaire sur volumes bind-mount (dev only)
- ✅ Confirmer que DATABASE_URL et REDIS_URL utilisent hostnames (postgres/redis) - déjà OK
- ✅ Confirmer port mapping 8001 - déjà OK

### 2. Settings normalization
- ✅ Ajouter propriété `debug` dérivée de ENV: `debug = (ENV != "prod")`
- ✅ Changer default ENV à "local" dans settings.py pour cohérence
- ✅ Vérifier .env.example cohérence

### 3. Observability + trace_id
- ✅ Trace_id middleware déjà implémenté
- ⚠️ Vérifier que logging inclut trace_id automatiquement (via contextvars ou request.state)
- ✅ Ajouter trace_id dans les logs via Filter ou adapter le logger

### 4. Global error format
- ✅ Déjà implémenté correctement
- ⚠️ Vérifier que /ready retourne le bon status_code (503 si not_ready)

### 5. Health & readiness
- ✅ /health OK
- ⚠️ /ready doit retourner status_code 503 si not_ready (actuellement retourne 200)

### 6. Worker alignment
- ✅ Worker utilise déjà les mêmes env vars - OK
- ✅ Documenté dans README

### 7. Docs + README
- ✅ Ajouter commandes docker compose exactes
- ✅ Ajouter note sur volumes bind-mount (prod removes them)
- ✅ Clarifier URLs et migrations

## Fichiers à modifier

1. `infra/docker-compose.yml` - ENV default + commentaires
2. `backend/app/infrastructure/settings.py` - ajouter debug property, changer default ENV
3. `backend/app/api/public/health.py` - fix status_code pour /ready
4. `backend/app/infrastructure/logging_config.py` - améliorer injection trace_id dans logs
5. `backend/env.example` - changer ENV default à "local"
6. `README.md` - clarifier commandes et ajouter note prod

