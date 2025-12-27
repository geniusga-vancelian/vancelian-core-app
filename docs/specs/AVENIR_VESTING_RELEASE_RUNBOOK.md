# AVENIR Vesting Release Runbook

**Date:** 2025-01-27  
**Version:** 1.0  
**Status:** 📋 Runbook

---

## Objectif

Ce document explique comment utiliser le système de release automatique des lots AVENIR matures.

---

## Endpoints

### 1. Admin: Déclencher le Release

**Endpoint:** `POST /api/v1/admin/vaults/AVENIR/vesting/release`

**Authentification:** Requiert rôle ADMIN

**Query Parameters:**
- `as_of` (optional): Date pour vérifier la maturité (format: YYYY-MM-DD, default: aujourd'hui UTC)
- `currency` (optional): Devise (default: "AED")
- `dry_run` (optional): Simulation sans commit (default: false)

**Exemple cURL:**
```bash
# Dry-run (simulation)
curl -X POST "http://localhost:8000/api/v1/admin/vaults/AVENIR/vesting/release?dry_run=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json"

# Release réel (aujourd'hui)
curl -X POST "http://localhost:8000/api/v1/admin/vaults/AVENIR/vesting/release" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json"

# Release pour une date spécifique
curl -X POST "http://localhost:8000/api/v1/admin/vaults/AVENIR/vesting/release?as_of=2026-01-15" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json"
```

**Réponse:**
```json
{
  "matured_found": 5,
  "executed_count": 5,
  "executed_amount": "50000.00",
  "skipped_count": 0,
  "errors_count": 0,
  "errors": [],
  "trace_id": "abc-123-def-456",
  "as_of_date": "2025-01-27"
}
```

### 2. Client: Timeline

**Endpoint:** `GET /api/v1/vaults/AVENIR/vesting/timeline?currency=AED`

**Authentification:** Requiert rôle USER

**Query Parameters:**
- `currency` (optional): Devise (default: "AED")

**Exemple cURL:**
```bash
curl "http://localhost:8000/api/v1/vaults/AVENIR/vesting/timeline?currency=AED" \
  -H "Authorization: Bearer $USER_TOKEN"
```

**Réponse:**
```json
{
  "vault_code": "AVENIR",
  "currency": "AED",
  "items": [
    {
      "date": "2026-01-15",
      "amount": "10000.00"
    },
    {
      "date": "2026-02-20",
      "amount": "5000.00"
    }
  ]
}
```

---

## Workflow Recommandé

### 1. Vérifier les lots matures (dry-run)

```bash
curl -X POST "http://localhost:8000/api/v1/admin/vaults/AVENIR/vesting/release?dry_run=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Vérifier:**
- `matured_found`: Nombre de lots matures trouvés
- `executed_count`: Nombre qui seraient libérés
- `executed_amount`: Montant total qui serait libéré
- `errors_count`: Doit être 0

**Note importante:** `dry_run=true` ne crée **AUCUNE** Operation, LedgerEntry, ou modification de lot. C'est une simulation pure qui calcule uniquement les statistiques.

### 2. Exécuter le release réel

```bash
curl -X POST "http://localhost:8000/api/v1/admin/vaults/AVENIR/vesting/release" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Vérifier:**
- `executed_count` > 0
- `errors_count` == 0
- `executed_amount` correspond aux attentes

### 3. Vérifier les transactions

Les opérations `VAULT_VESTING_RELEASE` doivent apparaître dans:
- `/api/v1/transactions` (historique utilisateur)
- Dashboard frontend

### 4. Vérifier les balances

- `WALLET_AVAILABLE` doit avoir augmenté
- `WALLET_LOCKED` doit avoir diminué
- Wallet Matrix doit refléter les changements

---

## Idempotence

Le système est **idempotent** : l'idempotence est basée sur le `status` et `released_amount` du lot, **pas** sur le `trace_id`.

**Règle:** Un lot est skip si:
- `status == 'RELEASED'` OU
- `released_amount >= amount`

Le `trace_id` est utilisé uniquement pour l'**observabilité** (traçabilité), pas comme garde-fou comptable.

**Exemple:**
```bash
# Run 1
curl -X POST "http://localhost:8000/api/v1/admin/vaults/AVENIR/vesting/release" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
# Response: executed_count=5, trace_id="abc-123"

# Run 2 (immédiatement après, même ou différent trace_id)
curl -X POST "http://localhost:8000/api/v1/admin/vaults/AVENIR/vesting/release" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
# Response: executed_count=0, skipped_count=5
# (Les lots sont déjà RELEASED, donc skip même avec trace_id différent)
```

---

## Rejouabilité

Le système est **rejouable** : après une erreur, un nouveau run peut traiter les lots restants.

**Scénario:**
```
Run 1: trace_id="abc-123", traite lot #1 (status=RELEASED), erreur sur lot #2 (status=VESTED)
Run 2: trace_id="def-456", lot #1 → skip (status=RELEASED), lot #2 → traite (status=VESTED)
```

**Note:** La rejouabilité fonctionne car l'idempotence est basée sur `status`, pas sur `trace_id`.

---

## Vérification en Base de Données

### Vérifier les lots libérés

```sql
SELECT 
    COUNT(*) as released_count,
    SUM(released_amount) as total_released
FROM vault_vesting_lots
WHERE status = 'RELEASED'
  AND vault_code = 'AVENIR';
```

### Vérifier les opérations de release

```sql
SELECT 
    id,
    created_at,
    operation_metadata->>'release_amount' as amount,
    operation_metadata->>'trace_id' as trace_id
FROM operations
WHERE type = 'VAULT_VESTING_RELEASE'
ORDER BY created_at DESC
LIMIT 10;
```

### Vérifier les ledger entries

```sql
SELECT 
    le.entry_type,
    a.account_type,
    SUM(le.amount) as total
FROM ledger_entries le
JOIN accounts a ON le.account_id = a.id
JOIN operations o ON le.operation_id = o.id
WHERE o.type = 'VAULT_VESTING_RELEASE'
GROUP BY le.entry_type, a.account_type;
```

---

## Timeline Utilisateur

### Accès Frontend

1. Aller sur le dashboard: `http://localhost:3000`
2. Cliquer sur "Vesting timeline" dans la section AVENIR
3. Ou accéder directement: `http://localhost:3000/vaults/avenir/vesting`

### Affichage

- Timeline verticale avec dates de release
- Montants agrégés par date
- Total restant à libérer
- Format monétaire localisé

---

## Wallet Locks Closure

### Comportement

Lors du release d'un lot AVENIR, le système ferme automatiquement les `wallet_locks` correspondants:

1. **Recherche du lock:**
   - **Priorité 1:** Via `operation_id == source_operation_id` (lien direct)
   - **Priorité 2 (fallback):** Si introuvable, recherche par:
     - `user_id`, `currency`, `reason=VAULT_AVENIR_VESTING`, `status=ACTIVE`
     - `reference_id == vault_id`
     - `amount` proche de `lot.amount` (tolérance ±0.01)
     - `created_at` même jour que `deposit_day`

2. **Fermeture:**
   - Si `wallet_lock.amount <= release_amount`: Full release (`status=RELEASED`)
   - Sinon: Partial release (crée nouveau lock pour remaining)

3. **Si lock introuvable:**
   - Logger warning avec `trace_id`
   - **NE PAS** échouer le release (ledger prime)
   - Incrémenter `locks_missing_count` dans summary

### Vérification

**Dans le summary:**
```json
{
  "locks_closed_count": 3,
  "locks_missing_count": 0
}
```

**En DB:**
```sql
-- Vérifier locks fermés pour une date
SELECT 
    COUNT(*) as released_locks_count
FROM wallet_locks
WHERE reason = 'VAULT_AVENIR_VESTING'
  AND status = 'RELEASED'
  AND DATE(released_at) = '2025-01-27';
```

**Wallet Matrix:**
- Après release, `AVENIR locked` doit diminuer
- Si `locks_missing_count > 0`, la wallet-matrix peut encore afficher locked (incohérence)

### Debug si Mismatch

**Problème:** `locks_missing_count > 0`

**Causes possibles:**
1. Lock créé sans `operation_id` (ancien code)
2. `source_operation_id` du lot ne correspond pas à `operation_id` du lock
3. Lock déjà fermé manuellement

**Solution:**
1. Vérifier le lock en DB:
```sql
SELECT * FROM wallet_locks
WHERE user_id = '<user_id>'
  AND reason = 'VAULT_AVENIR_VESTING'
  AND status = 'ACTIVE'
  AND reference_id = '<vault_id>';
```

2. Vérifier le lot:
```sql
SELECT source_operation_id, deposit_day, amount
FROM vault_vesting_lots
WHERE id = '<lot_id>';
```

3. Si lock existe mais non trouvé:
   - Vérifier que `operation_id` du lock = `source_operation_id` du lot
   - Si différent, fermer manuellement le lock:
```sql
UPDATE wallet_locks
SET status = 'RELEASED', released_at = NOW()
WHERE id = '<lock_id>';
```

---

## Troubleshooting

### Problème: `executed_count = 0` mais `matured_found > 0`

**Causes possibles:**
- Lots déjà libérés (vérifier `status = 'RELEASED'`)
- Balance `WALLET_LOCKED` insuffisante
- Erreurs transactionnelles (vérifier `errors`)

**Solution:**
- Vérifier les `errors` dans la réponse
- Vérifier les balances utilisateur
- Vérifier les logs backend

### Problème: Double-comptage

**Cause:** Exécution simultanée avec même `trace_id` (rare)

**Solution:**
- Le système est conçu pour éviter cela (idempotence)
- Si problème, vérifier les `release_job_trace_id` dans `vault_vesting_lots`

### Problème: Timeline vide

**Causes possibles:**
- Aucun lot VESTED pour l'utilisateur
- Tous les lots déjà RELEASED
- Filtre currency incorrect

**Solution:**
- Vérifier les lots en DB: `SELECT * FROM vault_vesting_lots WHERE user_id = '<uuid>' AND status = 'VESTED'`
- Vérifier le currency utilisé

---

## Commandes Utiles

**Compter les lots matures:**
```sql
SELECT COUNT(*) 
FROM vault_vesting_lots 
WHERE vault_code = 'AVENIR'
  AND release_day <= CURRENT_DATE
  AND status = 'VESTED'
  AND released_amount < amount;
```

**Voir les prochaines dates de release:**
```sql
SELECT 
    release_day,
    COUNT(*) as lot_count,
    SUM(amount - released_amount) as total_remaining
FROM vault_vesting_lots
WHERE vault_code = 'AVENIR'
  AND status = 'VESTED'
GROUP BY release_day
ORDER BY release_day ASC
LIMIT 10;
```

---

**Dernière mise à jour:** 2025-01-27

