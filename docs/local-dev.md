# Guide de développement local

## Prérequis

- Docker et Docker Compose
- Python 3.12+ (optionnel, si développement sans Docker)
- PostgreSQL 15+ (optionnel, si développement sans Docker)
- Redis 7+ (optionnel, si développement sans Docker)

## Démarrage avec Docker Compose (Recommandé)

### 1. Configuration de l'environnement

```bash
# Copier le fichier d'exemple
cp backend/.env.example backend/.env

# Éditer backend/.env si nécessaire (par défaut, les valeurs fonctionnent avec docker-compose)
```

### 2. Démarrer tous les services

```bash
# Depuis la racine du projet
make up

# Ou directement
cd infra && docker compose up -d
```

Cela démarre:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Backend FastAPI (port 8001)
- Worker RQ (en arrière-plan)

### 3. Appliquer les migrations

```bash
make migrate

# Ou directement
cd infra && docker compose exec backend alembic upgrade head
```

### 4. Vérifier que tout fonctionne

```bash
# Health check
curl http://localhost:8001/health

# Readiness check (vérifie DB et Redis)
curl http://localhost:8001/ready
```

### 5. Accéder à l'API

- **API**: http://localhost:8001
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

## Commandes utiles (Makefile)

```bash
# Démarrer les services
make up

# Arrêter les services
make down

# Voir les logs
make logs                # Tous les services
make logs-backend        # Backend uniquement
make logs-worker         # Worker uniquement

# Migrations
make migrate             # Appliquer les migrations
make migrate-create msg="description"  # Créer une nouvelle migration

# Tests
make test                # Lancer les tests pytest

# Shell
make shell               # Shell dans le conteneur backend
make shell-db            # Shell PostgreSQL
```

## Développement sans Docker

### 1. Installer les dépendances

```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Démarrer PostgreSQL et Redis localement

```bash
# PostgreSQL
# (selon votre système: brew install postgresql, apt-get install postgresql, etc.)
createdb vancelian_core

# Redis
# (selon votre système: brew install redis, apt-get install redis, etc.)
redis-server
```

### 3. Configurer l'environnement

```bash
cd backend
cp .env.example .env

# Éditer .env avec les URLs locales:
# DATABASE_URL=postgresql://user:password@localhost:5432/vancelian_core
# REDIS_URL=redis://localhost:6379/0
```

### 4. Appliquer les migrations

```bash
cd backend
alembic upgrade head
```

### 5. Démarrer le backend

```bash
cd backend
uvicorn app.main:app --reload --port 8001
```

### 6. Démarrer le worker (dans un autre terminal)

```bash
cd backend
python -m app.workers.worker
```

## Créer une nouvelle migration

```bash
# Avec Docker
make migrate-create msg="add_new_field_to_users"

# Ou directement
cd infra && docker compose exec backend alembic revision --autogenerate -m "add_new_field_to_users"

# Sans Docker
cd backend && alembic revision --autogenerate -m "add_new_field_to_users"
```

## Exécuter les tests

```bash
# Avec Docker
make test

# Ou directement
cd infra && docker compose exec backend pytest

# Sans Docker
cd backend && pytest
```

## Débogage

### Voir les logs du backend

```bash
make logs-backend

# Ou en temps réel
cd infra && docker compose logs -f backend
```

### Accéder à la base de données

```bash
# Shell PostgreSQL
make shell-db

# Ou directement
cd infra && docker compose exec postgres psql -U vancelian -d vancelian_core
```

### Accéder au shell du backend

```bash
make shell

# Ou directement
cd infra && docker compose exec backend /bin/bash
```

## Variables d'environnement

Voir `backend/.env.example` pour la liste complète des variables.

Variables principales:
- `DATABASE_URL`: URL de connexion PostgreSQL
- `REDIS_URL`: URL de connexion Redis
- `SECRET_KEY`: Clé secrète (changez en production!)
- `ALLOWED_ORIGINS`: Origines CORS autorisées (séparées par des virgules)
- `LOG_LEVEL`: Niveau de log (DEBUG, INFO, WARNING, ERROR)
