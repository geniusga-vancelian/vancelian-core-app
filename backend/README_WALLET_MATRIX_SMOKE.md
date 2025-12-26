# Wallet Matrix - Smoke Tests & Checklist

**Date:** 2025-01-26  
**Version:** v2  
**Endpoint:** `GET /api/v1/dev/wallet-matrix`

---

## Objectif

Ce document fournit une checklist scriptable pour valider que la Wallet Matrix respecte les règles métier canoniques :
- AED(USER).locked est TOUJOURS "0.00"
- Les montants investis apparaissent sous l'instrument (Offer/Vault) dans la bonne colonne
- Aucun double comptage
- Les cas ZAND blocked restent corrects

---

## 1. Commandes Docker pour démarrer le backend

```bash
# Depuis la racine du projet
cd backend

# Démarrer les services (PostgreSQL, Redis, etc.)
docker-compose -f ../docker-compose.dev.yml up -d postgres redis

# Attendre que PostgreSQL soit prêt
sleep 5

# Appliquer les migrations
alembic upgrade head

# Démarrer le serveur backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Alternative (si déjà en cours d'exécution):**
```bash
# Vérifier que le backend tourne
curl http://localhost:8000/health
```

---

## 2. Commandes cURL pour tester l'endpoint

### 2.1. Wallet Matrix (sans système wallets)

```bash
# Remplacer YOUR_TOKEN par un token valide (obtenu via /api/v1/auth/login)
curl -X GET "http://localhost:8000/api/v1/dev/wallet-matrix" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" | jq
```

**Résultat attendu:**
- Status: `200 OK`
- `rows` contient au minimum une ligne `"AED (USER)"`
- `rows[0].locked == "0.00"` (toujours)
- Si des investissements existent, des lignes `"OFFRE — <name>"` apparaissent
- Si des positions vault existent, des lignes `"COFFRE — <code>"` apparaissent

### 2.2. Wallet Matrix (avec système wallets)

```bash
curl -X GET "http://localhost:8000/api/v1/dev/wallet-matrix?show_system=true" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" | jq
```

**Résultat attendu:**
- Status: `200 OK`
- Même structure que ci-dessus
- Des lignes supplémentaires avec `"row_kind": "OFFER_SYSTEM"` ou `"VAULT_SYSTEM"` apparaissent
- Ces lignes ont un badge `(SYSTEM)` dans le label

---

## 3. Checklist visuelle sur le dashboard

### 3.1. Ouvrir le dashboard

1. Aller sur `http://localhost:3000`
2. Se connecter si nécessaire
3. Vérifier que le bloc **"Wallet Matrix (DEV)"** est visible (uniquement en mode DEV)

### 3.2. Test 1: AED locked = 0 (toujours)

**Action:**
- Observer la ligne "AED (USER)" dans le tableau

**Vérification:**
- [ ] Colonne "Locked" = `0.00` (toujours, même si des investissements existent)
- [ ] Colonne "Available" = montant disponible (peut être > 0)
- [ ] Colonne "Blocked" = montant en review (peut être > 0)

**Règle métier:** Les montants "locked" doivent apparaître dans les lignes instruments (Offer/Vault), pas dans AED.

### 3.3. Test 2: Offer row locked augmente après invest

**Action:**
1. Investir dans une offre via `/invest` (ou via API)
2. Recharger le dashboard
3. Observer la ligne "OFFRE — <name>"

**Vérification:**
- [ ] Une ligne "OFFRE — <name>" apparaît après l'investissement
- [ ] Colonne "Locked" = montant investi (ex: `5000.00`)
- [ ] Colonne "Available" = `0.00`
- [ ] Colonne "Blocked" = `0.00`
- [ ] Sous-texte "Position: X AED" apparaît sous le label

**Règle métier:** L'investissement apparaît dans la colonne "Locked" de la ligne Offer, pas dans AED.

### 3.4. Test 3: Vault FLEX va dans available

**Action:**
1. Déposer dans le coffre FLEX via le dashboard (ou via API)
2. Recharger le dashboard
3. Observer la ligne "COFFRE — FLEX"

**Vérification:**
- [ ] Une ligne "COFFRE — FLEX" apparaît après le dépôt
- [ ] Colonne "Available" = position principal (ex: `10000.00`)
- [ ] Colonne "Locked" = `0.00`
- [ ] Colonne "Blocked" = `0.00`
- [ ] Sous-texte "Position: X AED" apparaît sous le label

**Règle métier:** FLEX est un coffre liquide, donc la position va dans "Available".

### 3.5. Test 4: Vault AVENIR va dans locked

**Action:**
1. Déposer dans le coffre AVENIR via le dashboard (ou via API)
2. Recharger le dashboard
3. Observer la ligne "COFFRE — AVENIR"

**Vérification:**
- [ ] Une ligne "COFFRE — AVENIR" apparaît après le dépôt
- [ ] Colonne "Available" = `0.00`
- [ ] Colonne "Locked" = position principal (ex: `20000.00`) - **vesting**
- [ ] Colonne "Blocked" = `0.00`
- [ ] Sous-texte "Position: X AED" apparaît sous le label

**Règle métier:** AVENIR est un coffre avec vesting, donc la position va dans "Locked".

### 3.6. Test 5: Toggle "Show system wallets" affiche les lignes SYSTEM

**Action:**
1. Cocher la checkbox "Show system wallets"
2. Observer le tableau

**Vérification:**
- [ ] Des lignes supplémentaires apparaissent en bas du tableau
- [ ] Ces lignes ont un badge "SYSTEM" à côté du label
- [ ] Un séparateur "System" apparaît entre les lignes USER et SYSTEM
- [ ] Les lignes SYSTEM ont `row_kind` = `"OFFER_SYSTEM"` ou `"VAULT_SYSTEM"`

**Règle métier:** Les wallets système sont affichés séparément pour le debugging, mais ne sont pas mélangés avec les lignes user.

### 3.7. Test 6: Bouton Refresh recharge les données

**Action:**
1. Effectuer une action (invest, dépôt, etc.)
2. Cliquer sur "Refresh"
3. Observer que les données se mettent à jour

**Vérification:**
- [ ] Le bouton "Refresh" recharge les données sans recharger la page
- [ ] Les nouvelles positions apparaissent après refresh
- [ ] Pas d'erreur dans la console

---

## 4. Smoke Tests Backend (pytest)

### 4.1. Exécuter les tests

```bash
cd backend

# Exécuter tous les tests wallet matrix
pytest tests/test_wallet_matrix_smoke.py -v

# Exécuter un test spécifique
pytest tests/test_wallet_matrix_smoke.py::test_wallet_matrix_aed_locked_always_zero -v
```

### 4.2. Tests disponibles

1. **`test_wallet_matrix_aed_locked_always_zero`**
   - Vérifie que AED(USER).locked est toujours "0.00"
   - Teste la règle canonique fondamentale

2. **`test_wallet_matrix_offer_row_appears_when_invested`**
   - Vérifie qu'une ligne OFFER_USER apparaît après investissement
   - Vérifie que locked = montant investi
   - Vérifie que AED locked reste à 0.00 (anti-double-counting)

3. **`test_wallet_matrix_vault_mapping_columns`**
   - Vérifie que FLEX va dans available
   - Vérifie que AVENIR va dans locked
   - Vérifie que AED locked reste à 0.00

4. **`test_wallet_matrix_no_double_counting`**
   - Vérifie qu'il n'y a pas de double comptage entre AED et instruments
   - Vérifie que les montants investis n'apparaissent pas dans AED locked

---

## 5. Exemple de JSON de réponse

```json
{
  "currency": "AED",
  "columns": ["available", "locked", "blocked"],
  "rows": [
    {
      "label": "AED (USER)",
      "row_kind": "USER_AED",
      "scope": {
        "type": "USER",
        "id": null,
        "owner": "USER"
      },
      "available": "10000.00",
      "locked": "0.00",
      "blocked": "500.00",
      "meta": {},
      "offer_id": null,
      "vault_id": null,
      "position_principal": null
    },
    {
      "label": "OFFRE — Test Offer Investment",
      "row_kind": "OFFER_USER",
      "scope": {
        "type": "OFFER",
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "owner": "USER"
      },
      "available": "0.00",
      "locked": "5000.00",
      "blocked": "0.00",
      "meta": {
        "offer_code": "TEST-OFFER",
        "offer_name": "Test Offer Investment"
      },
      "offer_id": "123e4567-e89b-12d3-a456-426614174000",
      "vault_id": null,
      "position_principal": "5000.00"
    },
    {
      "label": "COFFRE — FLEX",
      "row_kind": "VAULT_USER",
      "scope": {
        "type": "VAULT",
        "id": "123e4567-e89b-12d3-a456-426614174001",
        "owner": "USER"
      },
      "available": "10000.00",
      "locked": "0.00",
      "blocked": "0.00",
      "meta": {
        "vault_code": "FLEX"
      },
      "offer_id": null,
      "vault_id": "123e4567-e89b-12d3-a456-426614174001",
      "position_principal": "10000.00"
    }
  ],
  "meta": {
    "generated_at": "2025-01-26T10:00:00Z",
    "sim_version": "v2",
    "user_id": "123e4567-e89b-12d3-a456-426614174003"
  }
}
```

**Points clés:**
- `AED (USER).locked` = `"0.00"` (toujours)
- `OFFRE — <name>.locked` = montant investi
- `COFFRE — FLEX.available` = position principal
- `COFFRE — AVENIR.locked` = position principal (si AVENIR existe)

---

## 6. Invariants métier (assertions backend)

### 6.1. Invariant 1: AED locked = 0.00

**Code:** `backend/app/api/v1/dev.py` (ligne ~127)

```python
# INVARIANT: Force AED row locked to "0.00" regardless of WALLET_LOCKED balance
aed_locked = Decimal("0.00")
```

**Règle:** Même si `WALLET_LOCKED` a des fonds, on force `AED(USER).locked = "0.00"` pour respecter le canon métier.

### 6.2. Invariant 2: Anti-double-counting

**Code:** `backend/app/api/v1/dev.py` (ligne ~235)

```python
# ANTI-DOUBLE-COUNTING VALIDATION (log only, don't fail)
# If WALLET_LOCKED balance exists, it should match total_offer_invested + total_vault_locked
```

**Règle:** On vérifie (log seulement) que `WALLET_LOCKED` correspond à la somme des investissements + AVENIR vaults. Si mismatch, on log un warning mais on ne fait pas échouer l'endpoint (les règles d'affichage prennent le dessus).

---

## 7. Checklist rapide (scriptable)

```bash
# 1. Backend démarré
curl -f http://localhost:8000/health || echo "❌ Backend not running"

# 2. Endpoint accessible (nécessite token)
# curl -X GET "http://localhost:8000/api/v1/dev/wallet-matrix" \
#   -H "Authorization: Bearer $TOKEN" | jq '.rows[] | select(.row_kind == "USER_AED") | .locked'
# Résultat attendu: "0.00"

# 3. Tests passent
cd backend && pytest tests/test_wallet_matrix_smoke.py -v
```

---

## 8. Troubleshooting

### Problème: AED locked n'est pas 0.00

**Cause possible:** Bug dans l'endpoint (invariant non respecté)

**Solution:**
1. Vérifier les logs backend
2. Vérifier que l'invariant `aed_locked = Decimal("0.00")` est bien appliqué
3. Relancer les tests: `pytest tests/test_wallet_matrix_smoke.py::test_wallet_matrix_aed_locked_always_zero -v`

### Problème: Double comptage détecté

**Cause possible:** Mismatch entre `WALLET_LOCKED` et la somme des investissements

**Solution:**
1. Vérifier les logs backend (warning loggé)
2. Vérifier que les investissements sont bien trackés dans `InvestmentIntent` avec status `CONFIRMED`
3. Vérifier que les vaults AVENIR sont bien trackés dans `VaultAccount.principal`

### Problème: Tests échouent

**Cause possible:** Fixtures manquantes ou DB non initialisée

**Solution:**
1. Vérifier que `conftest.py` crée bien les fixtures nécessaires
2. Vérifier que la DB de test est accessible
3. Relancer avec `-v` pour plus de détails: `pytest tests/test_wallet_matrix_smoke.py -v -s`

---

## 9. Notes techniques

- **Pas de refactor:** On n'a pas modifié les flows existants (offers/partners/blog)
- **Garde-fous uniquement:** Les assertions sont des protections, pas des changements de logique
- **Logs informatifs:** Les warnings sont loggés mais n'empêchent pas l'endpoint de fonctionner
- **Tests isolés:** Chaque test crée ses propres données (pas de dépendances entre tests)

---

## 10. Résultats attendus des tests

| Test | Résultat attendu |
|------|------------------|
| `test_wallet_matrix_aed_locked_always_zero` | ✅ PASS - AED locked = "0.00" |
| `test_wallet_matrix_offer_row_appears_when_invested` | ✅ PASS - OFFER row avec locked > 0 |
| `test_wallet_matrix_vault_mapping_columns` | ✅ PASS - FLEX → available, AVENIR → locked |
| `test_wallet_matrix_no_double_counting` | ✅ PASS - Pas de double comptage |

---

**Dernière mise à jour:** 2025-01-26

