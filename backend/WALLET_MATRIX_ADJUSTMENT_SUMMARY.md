# WALLET MATRIX ADJUSTMENT — USER EXPOSURE ONLY

## ✅ CHANGEMENTS EFFECTUÉS

### Backend: `backend/app/api/v1/dev.py`

**Modifications:**
1. ✅ Ajout query param `show_system` (default: `false`)
2. ✅ Toujours inclure row "AED (USER)"
3. ✅ Vault rows: seulement si `VaultAccount.principal > 0`
4. ✅ Offer rows: seulement si `InvestmentIntent.status=CONFIRMED` et `allocated_amount > 0`
5. ✅ System rows: seulement si `show_system=true`
6. ✅ Ajout champs `offer_id`, `vault_id`, `position_principal` dans `WalletMatrixRow`

**Logique:**
- USER AED: toujours présent
- USER Vaults: query `VaultAccount` où `principal > 0` + join `Vault` pour status
- USER Offers: query `InvestmentIntent` avec `GROUP BY offer_id` et `SUM(allocated_amount)`
- SYSTEM rows: optionnelles via `show_system=true`

### Frontend: `frontend-client/app/dev/wallet-matrix/page.tsx`

**Modifications:**
1. ✅ Ajout types `offer_id`, `vault_id`, `position_principal` dans interface
2. ✅ Affichage "Position: X AED" sous le label si `position_principal > 0`
3. ✅ Suppression de l'hypothèse que les system rows existent toujours

---

## COMMANDE CURL

```bash
# 1. Obtenir token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"your_password"}' | jq -r '.access_token')

# 2. Appeler endpoint (user exposure only)
curl -X GET "http://localhost:8000/api/v1/dev/wallet-matrix" \
  -H "Authorization: Bearer ${TOKEN}" | jq

# 3. Appeler avec system rows (optionnel)
curl -X GET "http://localhost:8000/api/v1/dev/wallet-matrix?show_system=true" \
  -H "Authorization: Bearer ${TOKEN}" | jq
```

**Response attendue (user exposure only):**
```json
{
  "currency": "AED",
  "columns": ["available", "locked", "blocked"],
  "rows": [
    {
      "label": "AED (USER)",
      "scope": {"type": "USER", "id": null, "owner": "USER"},
      "available": "1000.00",
      "locked": "500.00",
      "blocked": "0.00",
      "meta": {},
      "offer_id": null,
      "vault_id": null,
      "position_principal": null
    },
    {
      "label": "VAULT FLEX",
      "scope": {"type": "VAULT", "id": "...", "owner": "USER"},
      "available": "0.00",
      "locked": "0.00",
      "blocked": "0.00",
      "meta": {"vault_code": "FLEX"},
      "offer_id": null,
      "vault_id": "...",
      "position_principal": "2000.00"
    },
    {
      "label": "OFFER OFFER-001",
      "scope": {"type": "OFFER", "id": "...", "owner": "USER"},
      "available": "0.00",
      "locked": "1000.00",
      "blocked": "0.00",
      "meta": {"offer_code": "OFFER-001", "offer_name": "Test Offer"},
      "offer_id": "...",
      "vault_id": null,
      "position_principal": "1000.00"
    }
  ],
  "meta": {
    "generated_at": "2025-01-26T...",
    "sim_version": "v1",
    "user_id": "..."
  }
}
```

---

## CHECKLIST DE VALIDATION MANUELLE

### Test 1: User frais (aucune position)
- [ ] Se connecter avec un user sans investissements/vaults
- [ ] Ouvrir `/dev/wallet-matrix`
- [ ] Vérifier: seulement 1 row "AED (USER)" visible

### Test 2: Après investissement dans une offer
- [ ] Investir dans une offer (via dashboard)
- [ ] Recharger `/dev/wallet-matrix`
- [ ] Vérifier: row "OFFER {code}" apparaît avec `locked > 0`
- [ ] Vérifier: sous-label "Position: X AED" s'affiche

### Test 3: Après souscription vault FLEX
- [ ] Faire un deposit dans vault FLEX
- [ ] Recharger `/dev/wallet-matrix`
- [ ] Vérifier: row "VAULT FLEX" apparaît avec `position_principal > 0`
- [ ] Vérifier: sous-label "Position: X AED" s'affiche

### Test 4: Optionnel — System rows
- [ ] Appeler `/dev/wallet-matrix?show_system=true`
- [ ] Vérifier: system rows apparaissent (fond bleu)

---

## FICHIERS MODIFIÉS

### Backend
- ✅ `backend/app/api/v1/dev.py` (ADJUSTED — logique de sélection)

### Frontend
- ✅ `frontend-client/app/dev/wallet-matrix/page.tsx` (ADJUSTED — affichage position_principal)

---

## STATUS

✅ Backend ajusté — rows user exposure seulement
✅ Frontend ajusté — affichage position_principal
✅ Query param `show_system` implémenté
✅ Prêt pour validation manuelle
