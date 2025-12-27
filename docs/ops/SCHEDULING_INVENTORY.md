# Scheduling Infrastructure Inventory

**Date:** 2025-01-27  
**Version:** 1.0  
**Status:** 📋 Inventory

---

## Recherche Effectuée

### 1. Schedulers dans le code

**Recherche:** `grep -r "APScheduler|schedule|cron|scheduler" backend/`

**Résultats:**
- Aucun scheduler récurrent trouvé dans le code backend
- Références trouvées uniquement dans la documentation (`AVENIR_VESTING_TECH_AUDIT.md`) mentionnant :
  - Infrastructure RQ existe mais pas de scheduler récurrent
  - Recommandation: APScheduler ou cron externe

### 2. Scripts existants

**Dossier:** `backend/scripts/`

**Scripts trouvés:**
- `backfill_avenir_vesting_lots.py` - Script de backfill (one-shot)
- `check_migrations.py` - Vérification migrations
- `debug_user_operations.py` - Debug operations
- `security_check.py` - Vérification sécurité
- `seed_vaults.py` - Seed données
- `smoke_deposit_sim.sh` - Simulation dépôts

**Pattern observé:**
- Scripts Python utilisent `sys.path.insert(0, '.')` pour imports
- Utilisent `app.infrastructure.database.get_db()` pour DB session
- Pattern argparse pour CLI args

### 3. Docker Compose

**Fichiers trouvés:**
- `docker-compose.dev.yml` - Dev environment
- `docker-compose.prod.yml` - Production
- `infra/docker-compose.yml` - Infrastructure
- `docker-compose.observability.yml` - Observability

**Services existants:**
- `postgres` - Database
- `backend` - API FastAPI
- `redis` - Cache/Queue (si RQ utilisé)
- Pas de service cron/jobs dédié

### 4. Workers / Jobs

**Recherche:** `grep -r "worker|job|rq|celery" backend/`

**Résultats:**
- Infrastructure RQ mentionnée dans audit mais pas de scheduler récurrent
- Pas de worker.py avec scheduler trouvé

---

## Conclusion

**État actuel:**
- ❌ Aucun scheduler récurrent en place
- ❌ Pas de service cron/jobs dans docker-compose
- ✅ Scripts Python existants avec pattern clair
- ✅ Infrastructure DB accessible via `app.infrastructure.database`

**Décision:**
Implémenter un **cron container** simple dans `docker-compose.dev.yml` :
- Service dédié `vancelian-jobs-dev`
- Utilise l'image backend existante (ou python:3.11-slim)
- Cron classique pour exécution quotidienne
- Script CLI Python qui appelle directement le service

**Avantages:**
- Simple et robuste
- Pas de dépendance à un scheduler in-process
- Facilement désactivable
- Rejouable manuellement via CLI

**Alternative considérée mais rejetée:**
- APScheduler in-process : plus complexe, nécessite worker dédié
- Celery : overkill pour un job quotidien

---

**Dernière mise à jour:** 2025-01-27

