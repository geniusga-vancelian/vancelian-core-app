# AVENIR Vesting Daily Job Runbook

**Date:** 2025-01-27  
**Version:** 1.0  
**Status:** 📋 Production Runbook

---

## Objectif

Ce document explique comment utiliser et opérer le job quotidien automatique de release AVENIR vesting.

---

## Architecture

### Pourquoi Cron Container ?

**Décision:** Utiliser un container cron dédié plutôt qu'un scheduler in-process (APScheduler/Celery).

**Avantages:**
- ✅ Simple et robuste (cron classique, éprouvé)
- ✅ Isolation: le job ne bloque pas l'API
- ✅ Facilement désactivable (commenter service dans docker-compose)
- ✅ Rejouable manuellement via CLI
- ✅ Observabilité: logs dans stdout/stderr du container
- ✅ Pas de dépendance à un scheduler complexe

**Service:** `vancelian-jobs-dev` dans `docker-compose.dev.yml`

---

## Configuration

### Variables d'Environnement

Le service cron utilise les mêmes variables que le backend :
- `DATABASE_URL`: Connection string PostgreSQL
- `TZ`: Timezone (UTC par défaut, important pour cron)

### Crontab

**Schedule:** `5 0 * * *` (00:05 UTC quotidien)

**Commande:**
```bash
cd /app && python -m scripts.run_avenir_vesting_release_job --currency AED
```

**Logs:** Redirigés vers stdout/stderr du container (visible via `docker logs`)

---

## Utilisation Locale (Dev)

### 1. Activer le Service Cron

**Par défaut:** Le service est activé dans `docker-compose.dev.yml`.

**Désactiver temporairement:**
```yaml
# Dans docker-compose.dev.yml, ajouter:
vancelian-jobs-dev:
  profiles:
    - jobs  # Nécessite --profile jobs pour démarrer
```

Puis démarrer avec:
```bash
docker-compose -f docker-compose.dev.yml --profile jobs up -d
```

**Réactiver:**
```bash
# Retirer le bloc profiles: ou commenter le service
docker-compose -f docker-compose.dev.yml up -d vancelian-jobs-dev
```

### 2. Exécution Manuelle (Run Once)

#### Dry-Run (Simulation)

```bash
# Dans le container backend
docker exec -it vancelian-backend-dev python /app/scripts/run_avenir_vesting_release_job.py --dry-run

# Ou via docker-compose run (crée un container temporaire)
docker-compose -f docker-compose.dev.yml run --rm backend python /app/scripts/run_avenir_vesting_release_job.py --dry-run
```

**Sortie attendue (JSON):**
```json
{
  "job": "avenir_vesting_release",
  "trace_id": "job-avenir-vesting-20250127-abc12345",
  "as_of": "2025-01-27",
  "currency": "AED",
  "dry_run": true,
  "summary": {
    "matured_found": 3,
    "executed_count": 3,
    "executed_amount": "30000.00",
    "skipped_count": 0,
    "errors_count": 0,
    "errors": [],
    "trace_id": "job-avenir-vesting-20250127-abc12345",
    "as_of_date": "2025-01-27"
  },
  "exit_code": 0
}
```

#### Run Réel (Aujourd'hui)

```bash
docker exec -it vancelian-backend-dev python /app/scripts/run_avenir_vesting_release_job.py
```

#### Rejouer une Date Passée

```bash
# Rejouer le 2025-01-27
docker exec -it vancelian-backend-dev python /app/scripts/run_avenir_vesting_release_job.py --as-of 2025-01-27

# Rejouer avec dry-run
docker exec -it vancelian-backend-dev python /app/scripts/run_avenir_vesting_release_job.py --as-of 2025-01-27 --dry-run
```

**Note:** Rejouer une date passée est **safe** car le job est idempotent (basé sur `status == RELEASED`).

---

## Vérification des Résultats

### 1. Via Logs du Container

```bash
# Voir les logs du service cron
docker logs vancelian-jobs-dev

# Suivre les logs en temps réel
docker logs -f vancelian-jobs-dev

# Filtrer les logs du job
docker logs vancelian-jobs-dev 2>&1 | grep "avenir_vesting_release"
```

### 2. Via Base de Données

#### Compter les Operations de Release pour une Date

```bash
# Dans le container postgres
docker exec -it vancelian-postgres-dev psql -U vancelian -d vancelian_core
```

```sql
-- Compter les operations VAULT_VESTING_RELEASE pour une date
SELECT 
    COUNT(*) as release_count,
    SUM((operation_metadata->>'release_amount')::numeric) as total_released
FROM operations
WHERE type = 'VAULT_VESTING_RELEASE'
  AND DATE(created_at) = '2025-01-27';
```

#### Voir les Dernières Operations

```sql
SELECT 
    id,
    created_at,
    operation_metadata->>'trace_id' as trace_id,
    operation_metadata->>'release_amount' as amount,
    operation_metadata->>'vault_code' as vault_code
FROM operations
WHERE type = 'VAULT_VESTING_RELEASE'
ORDER BY created_at DESC
LIMIT 10;
```

#### Vérifier les Lots Libérés

```sql
SELECT 
    COUNT(*) as released_lots_count,
    SUM(released_amount) as total_released
FROM vault_vesting_lots
WHERE status = 'RELEASED'
  AND DATE(last_released_at) = '2025-01-27';
```

### 3. Via Endpoint Transactions

```bash
# Vérifier que les releases apparaissent dans l'historique
curl "http://localhost:8000/api/v1/transactions?limit=50" \
  -H "Authorization: Bearer $USER_TOKEN" | \
  jq '.items[] | select(.operation_type == "VAULT_VESTING_RELEASE")'
```

**Attendu:**
```json
{
  "operation_type": "VAULT_VESTING_RELEASE",
  "product_label": "COFFRE AVENIR",
  "direction": "IN",
  "amount_display": "10000.00",
  "created_at": "2025-01-27T00:05:00Z"
}
```

---

## Rejouer une Date Passée

### Cas d'Usage

- **Erreur lors de l'exécution automatique:** Rejouer la date pour traiter les lots restants
- **Test:** Vérifier le comportement sur une date spécifique
- **Recovery:** Après un incident, rejouer les dates manquées

### Commande

```bash
# Rejouer 2025-01-27
docker exec -it vancelian-backend-dev python /app/scripts/run_avenir_vesting_release_job.py --as-of 2025-01-27

# Rejouer avec dry-run d'abord (recommandé)
docker exec -it vancelian-backend-dev python /app/scripts/run_avenir_vesting_release_job.py --as-of 2025-01-27 --dry-run
```

### Sécurité

**Idempotent = Safe Replay:**
- Si un lot est déjà `RELEASED`, il sera skip
- Pas de double-comptage
- Pas de double ledger entries

**Vérification avant replay:**
```sql
-- Voir les lots matures non libérés pour une date
SELECT 
    COUNT(*) as pending_lots,
    SUM(amount - released_amount) as pending_amount
FROM vault_vesting_lots
WHERE vault_code = 'AVENIR'
  AND release_day <= '2025-01-27'
  AND status = 'VESTED'
  AND released_amount < amount;
```

---

## Points de Sécurité

### 1. Idempotence

Le job est **idempotent** : exécuter plusieurs fois la même date ne crée pas de double-comptage.

**Mécanisme:**
- Skip si `status == 'RELEASED'`
- Skip si `released_amount >= amount`

**Test:**
```bash
# Run 1
docker exec -it vancelian-backend-dev python /app/scripts/run_avenir_vesting_release_job.py --as-of 2025-01-27

# Run 2 (immédiatement après)
docker exec -it vancelian-backend-dev python /app/scripts/run_avenir_vesting_release_job.py --as-of 2025-01-27
# Doit retourner: executed_count=0, skipped_count >= 1
```

### 2. Dry-Run

Le flag `--dry-run` garantit qu'**aucune** écriture DB n'est effectuée.

**Vérification:**
```bash
# Compter operations avant
docker exec -it vancelian-postgres-dev psql -U vancelian -d vancelian_core -c "SELECT COUNT(*) FROM operations WHERE type = 'VAULT_VESTING_RELEASE';"

# Dry-run
docker exec -it vancelian-backend-dev python /app/scripts/run_avenir_vesting_release_job.py --dry-run

# Compter operations après (même count)
docker exec -it vancelian-postgres-dev psql -U vancelian -d vancelian_core -c "SELECT COUNT(*) FROM operations WHERE type = 'VAULT_VESTING_RELEASE';"
```

### 3. Trace ID

Chaque exécution génère un `trace_id` unique pour l'observabilité:
- Format: `job-avenir-vesting-YYYYMMDD-<shortuuid>`
- Stocké dans `operation.operation_metadata['trace_id']`
- Permet de tracer toutes les operations d'un run

**Recherche par trace_id:**
```sql
SELECT 
    id,
    created_at,
    operation_metadata->>'trace_id' as trace_id
FROM operations
WHERE type = 'VAULT_VESTING_RELEASE'
  AND operation_metadata->>'trace_id' = 'job-avenir-vesting-20250127-abc12345';
```

---

## Troubleshooting

### Problème: Le service cron ne démarre pas

**Vérifier:**
```bash
# Voir les logs du service
docker logs vancelian-jobs-dev

# Vérifier que le service est démarré
docker ps | grep vancelian-jobs-dev
```

**Solution:**
- Vérifier que `postgres` est healthy
- Vérifier les variables d'environnement (DATABASE_URL)
- Vérifier que le script existe: `docker exec vancelian-jobs-dev ls -la /app/scripts/run_avenir_vesting_release_job.py`

### Problème: Le cron ne s'exécute pas

**Vérifier crontab:**
```bash
docker exec -it vancelian-jobs-dev crontab -l
```

**Vérifier timezone:**
```bash
docker exec -it vancelian-jobs-dev date
# Doit être en UTC
```

**Solution:**
- Vérifier que `TZ=UTC` est défini dans environment
- Redémarrer le service: `docker-compose -f docker-compose.dev.yml restart vancelian-jobs-dev`

### Problème: Le job échoue silencieusement

**Vérifier logs:**
```bash
docker logs vancelian-jobs-dev 2>&1 | tail -50
```

**Vérifier exit code:**
```bash
# Le script retourne exit_code=1 si errors_count > 0
# Vérifier dans les logs JSON
docker logs vancelian-jobs-dev 2>&1 | grep "exit_code" | tail -1
```

**Solution:**
- Vérifier les erreurs dans `summary.errors`
- Vérifier la connexion DB
- Vérifier les balances utilisateur (WALLET_LOCKED suffisant)

---

## Commandes Utiles

### Voir le Prochain Run

```bash
# Voir la prochaine date de release
docker exec -it vancelian-postgres-dev psql -U vancelian -d vancelian_core -c "
SELECT 
    release_day,
    COUNT(*) as lot_count,
    SUM(amount - released_amount) as total_remaining
FROM vault_vesting_lots
WHERE vault_code = 'AVENIR'
  AND status = 'VESTED'
GROUP BY release_day
ORDER BY release_day ASC
LIMIT 5;
"
```

### Vérifier l'État du Service

```bash
# Status du container
docker ps | grep vancelian-jobs-dev

# Logs récents
docker logs --tail 20 vancelian-jobs-dev

# Processus cron
docker exec -it vancelian-jobs-dev ps aux | grep cron
```

---

**Dernière mise à jour:** 2025-01-27

