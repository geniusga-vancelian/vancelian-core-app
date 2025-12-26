# DEV WALLET MATRIX — IMPLÉMENTATION

## ✅ PHASE 1 — BACKEND

### Fichier créé: `backend/app/api/v1/dev.py`
- Endpoint: `GET /api/v1/dev/wallet-matrix`
- Gated par `settings.debug` ou `ENV in (dev, local, development)`
- Requiert `require_user_role()` (JWT bearer)
- Retourne matrice avec:
  - USER wallet (AED)
  - SYSTEM wallets pour tous les vaults (FLEX/AVENIR)
  - SYSTEM wallets pour toutes les offers actives
  - USER positions dans vaults (VaultAccount)
  - USER positions dans offers (InvestmentIntent, avec flag `not_implemented: true`)

### Enregistré dans: `backend/app/api/v1/__init__.py`

---

## ✅ PHASE 2 — FRONTEND

### Fichier créé: `frontend-client/app/dev/wallet-matrix/page.tsx`
- Page React avec tableau
- Fetch via `apiRequest` (inclut automatiquement JWT bearer)
- Affiche:
  - Colonnes: Label | Available | Locked | Blocked
  - Rows avec couleurs: SYSTEM (bleu), USER POSITION (vert)
  - Bouton "Refresh"
  - Affiche `trace_id` en cas d'erreur

### Lien DEV ajouté: `frontend-client/app/page.tsx`
- Lien "🔧 DEV: Wallet Matrix" visible seulement si `isDev === true`
- Placé dans la barre de navigation du dashboard

---

## ✅ PHASE 3 — TESTS

### Fichier créé: `backend/tests/test_dev_wallet_matrix.py`
- Test: `test_dev_wallet_matrix_returns_rows` — vérifie structure et 3 colonnes
- Test: `test_dev_wallet_matrix_requires_dev_mode` — vérifie gate DEV

---

## COMMANDES CURL

```bash
# 1. Obtenir token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"your_password"}' | jq -r '.access_token')

# 2. Appeler endpoint
curl -X GET "http://localhost:8000/api/v1/dev/wallet-matrix" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" | jq
```

**Response attendue:**
```json
{
  "currency": "AED",
  "columns": ["available", "locked", "blocked"],
  "rows": [
    {
      "label": "USER — AED",
      "scope": {"type": "USER", "id": null, "owner": "USER"},
      "available": "0.00",
      "locked": "0.00",
      "blocked": "0.00",
      "meta": {}
    },
    {
      "label": "VAULT FLEX — SYSTEM",
      "scope": {"type": "VAULT", "id": "...", "owner": "SYSTEM"},
      "available": "0.00",
      "locked": "0.00",
      "blocked": "0.00",
      "meta": {"vault_code": "FLEX"}
    },
    ...
  ],
  "meta": {
    "generated_at": "2025-01-26T...",
    "sim_version": "v1",
    "user_id": "..."
  }
}
```

---

## FICHIERS MODIFIÉS/CRÉÉS

### Backend
- ✅ `backend/app/api/v1/dev.py` (NOUVEAU)
- ✅ `backend/app/api/v1/__init__.py` (MODIFIÉ — ajout router dev)
- ✅ `backend/tests/test_dev_wallet_matrix.py` (NOUVEAU)

### Frontend
- ✅ `frontend-client/app/dev/wallet-matrix/page.tsx` (NOUVEAU)
- ✅ `frontend-client/app/page.tsx` (MODIFIÉ — ajout lien DEV)

---

## DESCRIPTION DU RENDU

Le tableau affiche:
- **En-tête**: "Wallet Matrix (DEV)" + bouton Refresh + timestamp
- **Tableau**: 4 colonnes (Label, Available, Locked, Blocked)
- **Rows avec couleurs**:
  - SYSTEM rows: fond bleu clair (`bg-blue-50`)
  - USER POSITION rows: fond vert clair (`bg-green-50`)
  - USER row principale: fond blanc
- **Formatage**: Montants en currency format (AED 0.00)
- **Error handling**: Affiche code, message, trace_id en rouge si erreur

---

## STATUS

✅ Backend endpoint créé et testé
✅ Frontend page créée
✅ Lien DEV ajouté au dashboard
✅ Tests backend ajoutés
✅ Documentation complète
