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

Le système est **idempotent** : exécuter plusieurs fois avec le même `trace_id` ne crée pas de double-comptage.

**Exemple:**
```bash
# Run 1
curl -X POST "http://localhost:8000/api/v1/admin/vaults/AVENIR/vesting/release" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
# Response: executed_count=5

# Run 2 (immédiatement après)
curl -X POST "http://localhost:8000/api/v1/admin/vaults/AVENIR/vesting/release" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
# Response: executed_count=0, skipped_count=5
```

---

## Rejouabilité

Le système est **rejouable** : après une erreur, un nouveau run avec un nouveau `trace_id` peut traiter les lots restants.

**Scénario:**
```
Run 1: trace_id="abc-123", traite lot #1, erreur sur lot #2
Run 2: trace_id="def-456", lot #1 → skip (déjà traité), lot #2 → traite
```

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

