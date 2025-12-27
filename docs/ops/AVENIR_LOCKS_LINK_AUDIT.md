# AVENIR Locks ↔ Vesting Lots Link Audit

**Date:** 2025-01-27  
**Version:** 1.0  
**Status:** 🔍 Audit Report

---

## Question 1: Comment un wallet_lock AVENIR est lié au dépôt ?

### Réponse

**Fichier:** `backend/app/services/vault_service.py` (lignes 219-254)

**Lors du dépôt AVENIR:**
1. Une `Operation` de type `VAULT_DEPOSIT` est créée
2. `db.flush()` est appelé pour obtenir `operation.id`
3. Un `WalletLock` est créé avec:
   - `operation_id = operation.id` (ligne 242)
   - `reason = LockReason.VAULT_AVENIR_VESTING.value`
   - `reference_type = ReferenceType.VAULT.value`
   - `reference_id = vault.id`
   - `status = LockStatus.ACTIVE.value`
   - `user_id = user_id`
   - `amount = amount` (montant du dépôt)

**Clé de liaison:** `operation_id` du `WalletLock` = `id` de l'`Operation` du dépôt.

**Idempotence:** Vérification avant création (lignes 227-229):
```python
existing_lock = db.query(WalletLock).filter(
    WalletLock.operation_id == operation.id
).first()
```

Si un lock existe déjà avec ce `operation_id`, aucun nouveau lock n'est créé.

---

## Question 2: Est-ce que vault_vesting_lots stocke une référence vers operation ?

### Réponse

**Fichier:** `backend/app/core/vaults/models.py`

**Oui:** Le modèle `VestingLot` a:
- `source_operation_id` (UUID, ForeignKey vers `operations.id`, unique=True)
- Cette colonne est **obligatoire** (`nullable=False`)

**Lors du backfill:**
- `source_operation_id` est défini à partir de l'`Operation` du dépôt AVENIR

**Lors du release:**
- `last_release_operation_id` stocke l'`Operation` du release

**Conclusion:** `VestingLot.source_operation_id` = `Operation.id` du dépôt AVENIR.

---

## Question 3: Quelle est la meilleure clé de liaison ?

### Réponse

**Clé primaire (idéale):**
```
WalletLock.operation_id == VestingLot.source_operation_id
```

**Pourquoi:**
- ✅ Directe et unique (un dépôt = une operation = un lock = un lot)
- ✅ Déjà utilisée dans le code actuel (`vesting_service.py` ligne 255)
- ✅ Idempotente (pas de doublon possible)

**Fallback (si operation_id manquant):**
```
(user_id, currency, reason=VAULT_AVENIR_VESTING, status=ACTIVE, 
 reference_id=vault_id, amount ≈ lot.amount, created_at ≈ deposit_day)
```

**Risques du fallback:**
- ⚠️ Moins précis (plusieurs locks peuvent matcher)
- ⚠️ Risque de fermer le mauvais lock si plusieurs dépôts le même jour
- ⚠️ Nécessite prudence (vérifier amount et date)

**Recommandation:**
- **Priorité 1:** Utiliser `operation_id == source_operation_id`
- **Priorité 2 (fallback):** Si lock introuvable, logger warning mais ne pas échouer
- **Priorité 3:** Si plusieurs locks matchent (fallback), fermer le plus ancien (FIFO)

---

## État Actuel du Code

### Création Lock (vault_service.py)

**Ligne 227-229:** Vérifie idempotence via `operation_id`
**Ligne 233-244:** Crée `WalletLock` avec `operation_id=operation.id`

✅ **Correct:** Le lock est bien lié au dépôt via `operation_id`.

### Release Lock (vesting_service.py)

**Ligne 254-258:** Cherche lock via:
```python
WalletLock.operation_id == lot.source_operation_id
```

✅ **Correct:** La liaison est correcte.

**Ligne 260-275:** Met à jour le lock:
- Si `wallet_lock.amount <= release_amount`: Full release (status=RELEASED)
- Sinon: Partial release (crée nouveau lock pour remaining)

⚠️ **Problème potentiel:**
- Si le lock n'est pas trouvé (ligne 260: `if wallet_lock:`), le release continue mais le lock reste ACTIVE
- La wallet-matrix continuera d'afficher le montant locked même après release

**Impact:**
- Wallet Matrix AVENIR locked ne diminue pas après release
- Incohérence entre ledger (WALLET_LOCKED diminue) et wallet_locks (reste ACTIVE)

---

## Recommandations

### 1. Améliorer la Recherche du Lock

**Stratégie:**
1. **Priorité 1:** `operation_id == source_operation_id` (actuel)
2. **Priorité 2 (fallback):** Si introuvable, chercher par:
   - `user_id`, `currency`, `reason=VAULT_AVENIR_VESTING`, `status=ACTIVE`
   - `reference_id == vault_id`
   - `amount` proche de `lot.amount` (tolérance ±0.01)
   - `created_at` proche de `deposit_day` (même jour UTC)
3. **Priorité 3:** Si plusieurs locks matchent, prendre le plus ancien (FIFO)

### 2. Gestion des Erreurs

**Si lock introuvable:**
- Logger warning avec `trace_id`, `lot.id`, `source_operation_id`
- **NE PAS** échouer le release (ledger prime)
- Incrémenter compteur `locks_missing_count` dans summary

**Si plusieurs locks matchent (fallback):**
- Logger warning
- Fermer le plus ancien (FIFO)
- Incrémenter compteur `locks_closed_count`

### 3. Concurrency

**Utiliser `FOR UPDATE` sur les locks sélectionnés:**
```python
wallet_lock = db.query(WalletLock).filter(...).with_for_update().first()
```

Pour éviter que deux releases simultanés ferment le même lock.

---

## Correspondance Actuelle

| Élément | Champ | Valeur |
|---------|-------|--------|
| **VestingLot** | `source_operation_id` | UUID de l'Operation du dépôt |
| **WalletLock** | `operation_id` | UUID de l'Operation du dépôt |
| **Liaison** | `WalletLock.operation_id == VestingLot.source_operation_id` | ✅ Directe |

**Conclusion:** La liaison est correcte et directe. Le problème potentiel est la gestion du cas où le lock n'est pas trouvé.

---

**Dernière mise à jour:** 2025-01-27

