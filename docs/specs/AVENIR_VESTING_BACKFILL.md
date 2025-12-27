# AVENIR Vesting Lots Backfill

**Date:** 2025-01-27  
**Version:** 1.0  
**Status:** 📋 Documentation

---

## Objectif

Ce document explique comment exécuter le script de backfill pour reconstruire les lots de vesting AVENIR à partir de l'historique des dépôts existants.

---

## Prérequis

1. **Migration appliquée:** La table `vault_vesting_lots` doit exister dans la base de données
   ```bash
   # Vérifier que la migration est appliquée
   docker-compose -f docker-compose.dev.yml exec backend alembic current
   ```

2. **Base de données accessible:** Le backend doit être en cours d'exécution
   ```bash
   docker-compose -f docker-compose.dev.yml ps
   ```

---

## Exécution du Backfill

### Mode Dry-Run (Recommandé en premier)

Exécuter le script en mode simulation pour voir ce qui sera créé sans modifier la base de données :

```bash
docker-compose -f docker-compose.dev.yml exec backend python -m scripts.backfill_avenir_vesting_lots --dry-run
```

**Output attendu:**
```
================================================================================
AVENIR Vesting Lots Backfill
================================================================================
DRY RUN MODE - No changes will be committed
Currency: AED
================================================================================
Found 5 AVENIR deposit operations to process
[DRY RUN] Would create vesting lot for operation <uuid> (user=<uuid>, amount=10000.00, deposit_day=2025-01-15)
[DRY RUN] Would create vesting lot for operation <uuid> (user=<uuid>, amount=5000.00, deposit_day=2025-01-16)
...
================================================================================
Backfill Summary
================================================================================
Created: 5
Skipped (already exist): 0
Errors: 0
================================================================================
```

### Exécution Réelle

Une fois le dry-run validé, exécuter le backfill réel :

```bash
docker-compose -f docker-compose.dev.yml exec backend python -m scripts.backfill_avenir_vesting_lots
```

**Output attendu:**
```
================================================================================
AVENIR Vesting Lots Backfill
================================================================================
Currency: AED
================================================================================
Found 5 AVENIR deposit operations to process
Created vesting lot for operation <uuid> (user=<uuid>, amount=10000.00, deposit_day=2025-01-15)
Created vesting lot for operation <uuid> (user=<uuid>, amount=5000.00, deposit_day=2025-01-16)
...
================================================================================
Backfill Summary
================================================================================
Created: 5
Skipped (already exist): 0
Errors: 0
================================================================================
```

### Options Avancées

**Filtrer par currency:**
```bash
docker-compose -f docker-compose.dev.yml exec backend python -m scripts.backfill_avenir_vesting_lots --currency AED
```

**Filtrer par user_id:**
```bash
docker-compose -f docker-compose.dev.yml exec backend python -m scripts.backfill_avenir_vesting_lots --user-id <uuid>
```

**Limiter le nombre d'opérations:**
```bash
docker-compose -f docker-compose.dev.yml exec backend python -m scripts.backfill_avenir_vesting_lots --limit 100
```

**Combinaison d'options:**
```bash
docker-compose -f docker-compose.dev.yml exec backend python -m scripts.backfill_avenir_vesting_lots \
  --currency AED \
  --user-id <uuid> \
  --limit 50 \
  --dry-run
```

---

## Vérification en Base de Données

### Vérifier le nombre de lots créés

```sql
SELECT COUNT(*) FROM vault_vesting_lots;
```

### Vérifier les lots par user

```sql
SELECT 
    user_id,
    COUNT(*) as lot_count,
    SUM(amount) as total_amount,
    SUM(released_amount) as total_released,
    SUM(remaining_amount) as total_remaining
FROM vault_vesting_lots
GROUP BY user_id;
```

### Vérifier les lots par date de dépôt

```sql
SELECT 
    deposit_day,
    COUNT(*) as lot_count,
    SUM(amount) as total_amount
FROM vault_vesting_lots
GROUP BY deposit_day
ORDER BY deposit_day DESC;
```

### Vérifier les lots par date de release

```sql
SELECT 
    release_day,
    COUNT(*) as lot_count,
    SUM(amount) as total_amount,
    SUM(remaining_amount) as total_remaining
FROM vault_vesting_lots
WHERE status = 'VESTED'
GROUP BY release_day
ORDER BY release_day ASC;
```

### Vérifier un lot spécifique

```sql
SELECT 
    id,
    vault_code,
    user_id,
    currency,
    deposit_day,
    release_day,
    amount,
    released_amount,
    remaining_amount,
    status,
    source_operation_id,
    created_at
FROM vault_vesting_lots
WHERE source_operation_id = '<operation_uuid>';
```

### Vérifier la cohérence avec wallet_locks

```sql
-- Comparer les montants verrouillés
SELECT 
    'wallet_locks' as source,
    SUM(amount) as total_locked
FROM wallet_locks
WHERE reason = 'VAULT_AVENIR_VESTING'
  AND status = 'ACTIVE'
  AND reference_type = 'VAULT'
UNION ALL
SELECT 
    'vesting_lots' as source,
    SUM(remaining_amount) as total_locked
FROM vault_vesting_lots
WHERE status = 'VESTED';
```

---

## Idempotence

Le script est **idempotent** : il peut être exécuté plusieurs fois sans créer de doublons.

**Mécanisme:**
- Contrainte `UNIQUE(source_operation_id)` empêche les doublons
- Si un lot existe déjà pour une opération, il est ignoré (skipped)

**Exemple:**
```bash
# Première exécution
docker-compose -f docker-compose.dev.yml exec backend python -m scripts.backfill_avenir_vesting_lots
# Output: Created: 5, Skipped: 0

# Deuxième exécution (idempotent)
docker-compose -f docker-compose.dev.yml exec backend python -m scripts.backfill_avenir_vesting_lots
# Output: Created: 0, Skipped: 5
```

---

## Source de Vérité

Le script utilise les **opérations VAULT_DEPOSIT** comme source de vérité :

1. **Opérations:** `operations` avec `type = 'VAULT_DEPOSIT'`
2. **Métadonnées:** `operation_metadata.vault_code = 'AVENIR'`
3. **Ledger entries:** Pour extraire `user_id` et `amount`
   - DEBIT sur `WALLET_AVAILABLE` (user account) → `user_id` et `amount`
   - CREDIT sur `VAULT_POOL_CASH` (vault pool account)

**Calculs:**
- `deposit_day = DATE(operation.created_at)` (normalisé à minuit UTC)
- `release_day = deposit_day + 365 jours`
- `amount = ABS(ledger_entry.amount)` où `entry_type = DEBIT` et `account_type = WALLET_AVAILABLE`

---

## Gestion des Erreurs

Le script continue de traiter les opérations même en cas d'erreur sur certaines :

- **Erreurs non-bloquantes:** Loggées dans `stats['errors']` mais le script continue
- **Erreurs transactionnelles:** Rollback automatique pour l'opération en cours, continue avec les suivantes

**Exemples d'erreurs:**
- `user_id` introuvable (ledger entry manquante)
- `amount` invalide (négatif ou zéro)
- Vault AVENIR introuvable
- Contrainte de base de données (doublon, foreign key, etc.)

---

## Checklist de Validation

Après exécution du backfill, vérifier :

- [ ] Nombre de lots créés correspond au nombre d'opérations AVENIR
- [ ] `deposit_day` est normalisé à minuit UTC (pas d'heure)
- [ ] `release_day = deposit_day + 365 jours`
- [ ] `amount` correspond au montant du dépôt
- [ ] `released_amount = 0.00` pour tous les nouveaux lots
- [ ] `status = 'VESTED'` pour tous les nouveaux lots
- [ ] Pas de doublons (contrainte `UNIQUE(source_operation_id)`)
- [ ] Cohérence avec `wallet_locks` (montants similaires)

---

## Commandes Utiles

**Vérifier l'état de la migration:**
```bash
docker-compose -f docker-compose.dev.yml exec backend alembic current
docker-compose -f docker-compose.dev.yml exec backend alembic history
```

**Se connecter à PostgreSQL:**
```bash
docker-compose -f docker-compose.dev.yml exec postgres psql -U vancelian -d vancelian_core
```

**Compter les opérations AVENIR:**
```sql
SELECT COUNT(*) 
FROM operations 
WHERE type = 'VAULT_DEPOSIT' 
  AND operation_metadata->>'vault_code' = 'AVENIR';
```

---

**Dernière mise à jour:** 2025-01-27

