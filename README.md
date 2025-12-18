# Vancelian Core App

Application principale (Core) pour la plateforme Vancelian.

## Architecture

- **Backend** : FastAPI (Python 3.12) avec PostgreSQL
- **Workers** : RQ (Redis Queue) pour tâches asynchrones
- **Base de données** : PostgreSQL 15+
- **Cache/Queue** : Redis 7+
- **Documentation** : Voir `VANCELIAN_SYSTEM.md` pour l'architecture complète

## Structure du projet

```
vancelian-core-app/
├── backend/               # Backend FastAPI
│   ├── app/              # Application principale
│   │   ├── main.py       # Point d'entrée FastAPI
│   │   ├── core/         # Domaines métier
│   │   ├── api/          # Routes API
│   │   ├── infrastructure/ # DB, Redis, settings, logging
│   │   ├── services/     # Logique applicative
│   │   ├── workers/      # RQ workers
│   │   ├── schemas/      # Schémas Pydantic
│   │   ├── security/     # RBAC et auth
│   │   └── utils/        # Utilitaires
│   ├── alembic/          # Migrations Alembic
│   ├── tests/            # Tests pytest
│   └── requirements.txt  # Dépendances Python
├── infra/                # Infrastructure Docker
│   └── docker-compose.yml # Configuration Docker Compose
├── docs/                 # Documentation
└── VANCELIAN_SYSTEM.md   # Bible système (référence unique)
```

## Prérequis

- Docker et Docker Compose
- Python 3.12+ (si développement sans Docker)
- PostgreSQL 15+ (si développement sans Docker)
- Redis 7+ (si développement sans Docker)

## Démarrage rapide

### Avec Docker Compose (Recommandé)

1. **Configurer l'environnement** (optionnel pour local dev):
```bash
cp backend/env.example backend/.env
# Éditer backend/.env si nécessaire
```

2. **Démarrer tous les services**:
```bash
make up

# Ou directement:
cd infra && docker compose up -d
```

Cela démarre:
- PostgreSQL sur le port 5432
- Redis sur le port 6379
- Backend API sur le port 8001
- Worker RQ (en arrière-plan)

3. **Appliquer les migrations Alembic**:
```bash
make migrate

# Ou directement:
cd infra && docker compose exec backend alembic upgrade head
```

4. **Vérifier que tout fonctionne**:
```bash
# Health check
curl http://localhost:8001/health
# Expected: {"status":"ok"}

# Readiness check (vérifie DB + Redis)
curl http://localhost:8001/ready
# Expected: {"status":"ok","database":"connected","redis":"connected"}
```

> **Note Production**: Les volumes bind-mount (`../backend:/app`) dans `docker-compose.yml` sont pour le développement local uniquement. Supprimez la section `volumes` pour les déploiements en production.

### Commandes Make disponibles

```bash
make up              # Démarrer tous les services
make down            # Arrêter tous les services
make logs            # Voir les logs
make migrate         # Appliquer les migrations
make test            # Lancer les tests
make shell           # Shell dans le conteneur backend
```

Voir `docs/local-dev.md` pour plus de détails.

## URLs importantes

Une fois les services démarrés (`make up`), l'API est accessible sur:

- **API Root**: http://localhost:8001/
- **Health Check**: http://localhost:8001/health
- **Readiness Check**: http://localhost:8001/ready (vérifie DB + Redis)
- **Swagger UI (OpenAPI)**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

## Endpoints API

### Public
- `GET /health` - Health check basique
- `GET /ready` - Readiness check (DB + Redis)

### API v1 (à venir)
- Routes préfixées par `/api/v1/`

### Admin (à venir)
- Routes préfixées par `/admin/v1/`

### Webhooks (à venir)
- Routes préfixées par `/webhooks/v1/`

## Documentation

- **Architecture**: `docs/architecture.md`
- **Développement local**: `docs/local-dev.md`
- **Sécurité**: `docs/security.md`
- **Bible système**: `VANCELIAN_SYSTEM.md`

## Tests

```bash
# Avec Docker (recommandé)
make test

# Ou directement
cd infra && docker compose exec backend pytest

# Tests de smoke (vérification basique)
cd infra && docker compose exec backend pytest tests/test_health.py -v
```

## Format d'erreur

Toutes les erreurs retournent un format standardisé:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {...},
    "trace_id": "uuid-v4"
  }
}
```

Le `trace_id` est inclus dans le header `X-Trace-ID` de la réponse.

## Ledger Immutabilité

Le ledger financier (`LedgerEntry`) est **immuable**:
- ❌ Pas d'UPDATE
- ❌ Pas de DELETE
- ✅ Toute correction via une nouvelle Operation (ADJUSTMENT/REVERSAL)

Voir `docs/architecture.md` pour plus de détails.

## Ancien scaffold

L'ancien scaffold a été archivé dans `archive/initial_scaffold_20251218/` lors du debt reset.

## Licence

Propriétaire - Vancelian
