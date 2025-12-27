# AVENIR Vesting Release - Hardening Notes

**Date:** 2025-01-27  
**Version:** 1.0  
**Status:** 🔧 Hardening Checklist

---

## Risk Checklist

### 1. Dry-Run Écriture (CRITIQUE)

**Risque:** `dry_run=True` crée quand même des `Operation` et `LedgerEntry` puis rollback.

**Fichier:** `backend/app/services/vesting_service.py` (lignes 147-241)

**Problème:**
- Lignes 148-164: Crée `Operation` même en dry_run
- Lignes 168-187: Crée `LedgerEntry` même en dry_run
- Ligne 238-241: Rollback seulement à la fin

**Impact:** 
- Risque de pollution DB (même si rollback)
- Performance dégradée (création inutile)
- Confusion dans les logs

**Fix requis:** Brancher `dry_run` AVANT toute création d'objet DB.

---

### 2. Idempotence Basée sur Trace_ID (LOGIC ERROR)

**Risque:** Skip basé sur `lot.release_job_trace_id == trace_id` au lieu de `status == RELEASED`.

**Fichier:** `backend/app/services/vesting_service.py` (lignes 112-115)

**Problème:**
```python
if lot.release_job_trace_id == trace_id:
    stats['skipped_count'] += 1
    continue
```

**Impact:**
- Si trace_id différent, risque de double-release
- Idempotence fragile (dépend de trace_id)
- Devrait être basé sur `status == RELEASED` ou `released_amount == amount`

**Fix requis:** Skip si `status == RELEASED` OU `released_amount >= amount`. Trace_id = observabilité uniquement.

---

### 3. UTC Day Bucketing (POTENTIEL BUG)

**Risque:** `normalize_to_utc_midnight()` ne fait rien (retourne date tel quel).

**Fichier:** `backend/app/services/vesting_service.py` (lignes 30-32, 71-74)

**Problème:**
- Si `as_of_date` vient d'un datetime avec timezone locale, pas de normalisation
- `deposit_day` et `release_day` doivent être en UTC date

**Impact:**
- Risque de comparaison incorrecte si timezone mixte
- Edge case: dépôt à 23:59 UTC+1 pourrait être mal bucketé

**Fix requis:** Helper `to_utc_day(datetime)` qui extrait date UTC. Helper `parse_as_of(str)` qui parse en UTC date.

---

### 4. DB Locking / Concurrency (PERFORMANCE)

**Risque:** Pas de batching explicite, risque de long locks.

**Fichier:** `backend/app/services/vesting_service.py` (lignes 94-105)

**Problème:**
- `max_lots=1000` par défaut (trop élevé)
- Pas de commit intermédiaire
- Lock sur tous les lots en une fois

**Impact:**
- Long locks si beaucoup de lots
- Blocage autres transactions
- Timeout possible

**Fix requis:** Batching (ex: 200 lots par batch) avec commit intermédiaire. `max_lots` paramétrable.

---

### 5. Transactions History Label (COHÉRENCE)

**Risque:** `product_label` pourrait ne pas être "COFFRE AVENIR" pour `VAULT_VESTING_RELEASE`.

**Fichier:** `backend/app/api/v1/transactions.py` (lignes 283-309)

**Problème:**
- Logique `vault_code` depuis metadata
- Si metadata manquant, fallback à "COFFRE" générique

**Impact:**
- Affichage incohérent frontend
- Utilisateur confus

**Fix requis:** S'assurer que `VAULT_VESTING_RELEASE` a toujours `vault_code='AVENIR'` dans metadata. Test explicite.

---

### 6. Frontend Timeline Robustesse (UX)

**Risque:** Pas de gestion d'erreur explicite, pas de loading state clair.

**Fichier:** `frontend-client/app/vaults/avenir/vesting/page.tsx`

**Problème:**
- Gestion erreur basique
- Pas de retry automatique
- Format date pourrait être incohérent

**Impact:**
- UX dégradée si erreur réseau
- Confusion utilisateur

**Fix requis:** Améliorer gestion erreur, retry, format date stable.

---

### 7. Tests Manquants (COUVERTURE)

**Risque:** Pas de test pour dry_run, UTC day, transactions history.

**Fichier:** `backend/tests/test_avenir_vesting_release.py`

**Manque:**
- Test dry_run n'écrit rien
- Test UTC day bucketing
- Test transactions include release
- Test idempotence deux runs (nouveau trace_id)

**Fix requis:** Ajouter tests manquants.

---

### 8. Documentation Runbook (ALIGNMENT)

**Risque:** Runbook pourrait ne pas correspondre au code réel.

**Fichier:** `docs/specs/AVENIR_VESTING_RELEASE_RUNBOOK.md`

**Problème:**
- Commandes curl pourraient être obsolètes
- Sorties JSON pourraient ne pas correspondre

**Fix requis:** Vérifier et aligner avec code réel.

---

## Priorités

1. **CRITIQUE:** Fix #1 (dry_run) - Risque de pollution DB
2. **CRITIQUE:** Fix #2 (idempotence) - Risque de double-release
3. **HAUTE:** Fix #3 (UTC day) - Risque de bugs edge case
4. **MOYENNE:** Fix #4 (batching) - Performance
5. **MOYENNE:** Fix #5 (transactions) - Cohérence UX
6. **BASSE:** Fix #6 (frontend) - UX amélioration
7. **HAUTE:** Fix #7 (tests) - Couverture
8. **MOYENNE:** Fix #8 (doc) - Alignement

---

**Dernière mise à jour:** 2025-01-27

