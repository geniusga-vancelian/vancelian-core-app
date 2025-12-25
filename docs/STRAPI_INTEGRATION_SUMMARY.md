# Strapi Integration Summary

## État d'Intégration

✅ **Infrastructure** : Strapi ajouté à docker-compose.dev.yml avec DB séparée  
✅ **Configuration** : i18n activé (fr/en/it), upload S3/R2 configuré  
✅ **Frontend Libs** : `frontend-client/lib/cms.ts` créé avec toutes les fonctions nécessaires  
✅ **Page Offer** : Intégration Strapi + fallback FastAPI  
✅ **Documentation** : Guides complets créés

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND CLIENT                       │
│  ┌──────────────────┐  ┌────────────────────────────┐   │
│  │  FastAPI Client  │  │   Strapi CMS Client        │   │
│  │  (Business)      │  │   (Marketing/Content)      │   │
│  └────────┬─────────┘  └───────────┬────────────────┘   │
└───────────┼────────────────────────┼────────────────────┘
            │                        │
            ▼                        ▼
┌──────────────────────┐  ┌──────────────────────┐
│   FASTAPI (8000)     │  │   STRAPI (1337)      │
│                      │  │                      │
│  • Investments       │  │  • Offer Marketing   │
│  • Wallets           │  │  • Offer Updates     │
│  • Transactions      │  │  • Articles          │
│  • Ledger            │  │  • Partners          │
│  • Offers (business) │  │  • Pages (site)      │
└──────────────────────┘  └──────────────────────┘
```

## Séparation des Responsabilités

### FastAPI (Business Logic)
- ✅ Investissements et transactions
- ✅ Wallets et ledger
- ✅ Gestion des offres (business data)
- ✅ Authentification et autorisation

### Strapi (Content Management)
- ✅ Marketing des offres (title, subtitle, highlights, why_invest, media, docs)
- ✅ Timeline/Updates des offres
- ✅ Articles/Blog
- ✅ Partenaires (profiles, projets)
- ✅ Pages marketing (site vitrine)
- ✅ Multi-langue (fr/en/it)

## Lien entre Strapi et FastAPI

Le lien se fait via `offer_id` (UUID string) :
- Pas de foreign key (loose coupling)
- FastAPI reste source de vérité pour business
- Strapi référence les UUIDs des offers FastAPI
- Frontend compose les deux sources

## Code Frontend

### Page Offer (`frontend-client/app/offers/[id]/page.tsx`)

**Charge** :
1. FastAPI : `offersApi.getOffer(offerId)` → Business data (amounts, status, etc.)
2. Strapi : `cms.getOfferMarketing(offerId)` → Marketing content
3. Strapi : `cms.getOfferUpdates(offerId)` → Timeline updates
4. Strapi : `cms.getArticlesByOfferId(offerId)` → Related articles

**Affiche** :
- Priorité Strapi, fallback FastAPI pour chaque section
- Si Strapi vide → affiche "Coming soon" ou utilise FastAPI

### Composant `OfferContentSections`

**Props** :
- `offer` : FastAPI Offer (business data)
- `marketing` : Strapi OfferMarketing (optional)
- `relatedOffers` : FastAPI Offers (business data)

**Logique** :
- Utilise `marketing` si disponible, sinon `offer.marketing_*`
- Médias : Strapi → FastAPI fallback
- Documents : Strapi → FastAPI fallback

## Content Types Strapi

Voir `docs/STRAPI_CONTENT_TYPES_SETUP.md` pour le guide détaillé.

**À créer manuellement dans Strapi Admin** :
1. Global (single type)
2. Page (collection)
3. OfferMarketing (collection)
4. OfferUpdate (collection)
5. Partner (collection)
6. PartnerProject (collection)
7. Article (collection)

## Permissions API

**Public Role** (Settings → Users & Permissions → Roles → Public) :
- ✅ `find` et `findOne` pour tous les content types
- ❌ Pas de `create`, `update`, `delete`
- ❌ Pas de `upload`

## Tests de Validation

```bash
# 1. Vérifier Strapi
docker compose -f docker-compose.dev.yml ps cms-strapi
curl http://localhost:1337/api/global?locale=fr

# 2. Vérifier frontend
# Ouvrir http://localhost:3000/offers/<id>
# Vérifier console : pas d'erreurs, URLs Strapi correctes

# 3. Audits
make audit-runtime
make audit-db
```

## Prochaines Étapes

1. **Démarrer Strapi** :
   ```bash
   docker compose -f docker-compose.dev.yml up -d cms-strapi
   ```

2. **Créer compte admin** : http://localhost:1337/admin

3. **Créer content types** : Suivre `docs/STRAPI_CONTENT_TYPES_SETUP.md`

4. **Configurer permissions** : Activer Public read pour tous les content types

5. **Tester** : Créer du contenu test et vérifier l'affichage dans le frontend

## Migration Contenu (Optionnel)

**Option A (Recommandé)** : Clean start
- Recréer le contenu marketing dans Strapi
- Plus propre, meilleure structure

**Option B** : Script migration
- Script ponctuel Postgres → Strapi
- À créer si nécessaire

## Notes Importantes

- ✅ **Aucun hardcode** : Toutes les URLs via `getStrapiApiUrl()` depuis `lib/config.ts`
- ✅ **Fallback gracieux** : Si Strapi indisponible, fallback FastAPI
- ✅ **Pas de régression** : FastAPI business logic intact
- ✅ **Multi-langue** : Support fr/en/it prêt
- ✅ **Storage** : R2/S3 configuré avec fallback local

## Fichiers Modifiés/Créés

### Backend
- `cms-strapi/` : Structure Strapi complète
- `docker-compose.dev.yml` : Service cms-strapi ajouté

### Frontend
- `frontend-client/lib/cms.ts` : Client CMS Strapi
- `frontend-client/lib/config.ts` : Fonctions Strapi URLs
- `frontend-client/app/offers/[id]/page.tsx` : Intégration Strapi
- `frontend-client/components/offers/OfferContentSections.tsx` : Support marketing Strapi

### Documentation
- `docs/CMS_STRAPI_RUNBOOK.md` : Guide complet Strapi
- `docs/STRAPI_CONTENT_TYPES_SETUP.md` : Guide création content types
- `docs/STRAPI_INTEGRATION_SUMMARY.md` : Ce fichier
- `docs/ENV_REFERENCE.md` : Variables Strapi documentées


