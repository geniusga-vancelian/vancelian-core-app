# Checklist Setup Strapi - Actions Manuelles

## État Actuel

✅ Infrastructure Strapi prête  
✅ Code frontend intégré  
⏳ Content types à créer (manuel)  
⏳ Permissions à configurer (manuel)  
⏳ Contenu de test à créer (manuel)

---

## STEP 1: Démarrer Strapi

### 1.1 Vérifier que Strapi démarre

```bash
# Vérifier le build
docker compose -f docker-compose.dev.yml up -d --build cms-strapi

# Attendre 30-60 secondes, puis vérifier
curl http://localhost:1337/admin
# Doit retourner 200 ou 302 (redirect to login)
```

### 1.2 Accéder à l'admin

Ouvrir dans le navigateur : **http://localhost:1337/admin**

---

## STEP 2: Créer le Compte Admin (si première fois)

Si Strapi demande de créer un admin :
- Email : votre email
- Password : mot de passe fort
- Confirm password : même mot de passe

**Sauvegarder ces identifiants** (vous en aurez besoin).

---

## STEP 3: Créer les Content Types

Suivre **EXACTEMENT** le guide : `docs/STRAPI_CONTENT_TYPES_SETUP.md`

**Ordre obligatoire :**
1. Global (Single Type)
2. Page (Collection)
3. OfferMarketing (Collection) ⚠️ **Important : champ `offer_id` (Text)**
4. OfferUpdate (Collection) ⚠️ **Important : champ `offer_id` (Text)**
5. Partner (Collection)
6. PartnerProject (Collection)
7. Article (Collection) ⚠️ **Important : champ `related_offer_ids` (JSON) OU `offer_id`**

**⚠️ Points critiques :**
- `OfferMarketing.offer_id` : Text, required, unique
- `OfferUpdate.offer_id` : Text, required
- `Article.related_offer_ids` : JSON (array de strings UUID)
- Tous les content types : **i18n activé** ✅

---

## STEP 4: Configurer les Permissions

Dans Strapi Admin :
1. **Settings** → **Users & Permissions** → **Roles** → **Public**
2. Pour chaque content type, activer **UNIQUEMENT** :
   - ✅ `find`
   - ✅ `findOne`
3. **NE PAS activer** :
   - ❌ `create`
   - ❌ `update`
   - ❌ `delete`
   - ❌ `upload`
4. **Save**

---

## STEP 5: Créer du Contenu de Test

### 5.1 Obtenir un offer_id depuis FastAPI

```bash
# Obtenir un UUID d'offre
curl -s http://localhost:8000/api/v1/offers | python3 -c "import sys, json; d=json.load(sys.stdin); print(d[0]['id'] if isinstance(d,list) and len(d) > 0 else 'NO_OFFERS')"

# Si NO_OFFERS, créer une offre via admin FastAPI d'abord
```

**Copier le UUID retourné** (ex: `123e4567-e89b-12d3-a456-426614174000`)

### 5.2 Créer Global (Single Type)

1. **Content Manager** → **Global**
2. Remplir au minimum :
   - `site_name` : "Vancelian"
   - `site_tagline` : "Your tagline"
3. **Save**
4. **Publish** (si disponible)

### 5.3 Créer OfferMarketing

1. **Content Manager** → **Offer Marketing** → **Create new entry**
2. Remplir :
   - `offer_id` : **Coller le UUID copié** (ex: `123e4567-e89b-12d3-a456-426614174000`)
   - `title` : "Test Offer Marketing"
   - `subtitle` : "Subtitle test"
   - `location` : "Paris, France"
   - `highlights` : Si JSON → `["Highlight 1", "Highlight 2"]` (format JSON array)
3. **Save**
4. **Publish**

### 5.4 Créer OfferUpdate (2 entrées)

1. **Content Manager** → **Offer Update** → **Create new entry**
2. Entry 1 :
   - `offer_id` : **Même UUID**
   - `title` : "Project Started"
   - `description` : "The project has officially started"
   - `date` : Date d'aujourd'hui
   - `status` : "MILESTONE"
3. **Save** et **Publish**
4. Entry 2 :
   - `offer_id` : **Même UUID**
   - `title` : "First Milestone Reached"
   - `description` : "We reached our first milestone successfully"
   - `date` : Date d'hier
   - `status` : "SUCCESS"
5. **Save** et **Publish**

### 5.5 Créer Article

1. **Content Manager** → **Article** → **Create new entry**
2. Remplir :
   - `title` : "Test Article"
   - `slug` : "test-article" (généré automatiquement depuis title)
   - `excerpt` : "This is a test article"
   - `status` : **"PUBLISHED"** (ou remplir `published_at`)
   - `related_offer_ids` : Si JSON → `["<UUID>"]` (array avec le UUID de l'offre)
3. **Save**
4. **Publish**

---

## STEP 6: Validation

### 6.1 Tester les Endpoints API

Remplacez `<OFFER_ID>` par le UUID réel.

```bash
# Global
curl -s "http://localhost:1337/api/global?locale=fr" | head -c 400

# OfferMarketing
curl -s "http://localhost:1337/api/offer-marketings?filters[offer_id][\$eq]=<OFFER_ID>&locale=fr&populate=*" | head -c 700

# OfferUpdates
curl -s "http://localhost:1337/api/offer-updates?filters[offer_id][\$eq]=<OFFER_ID>&locale=fr&sort=date:desc&populate=*" | head -c 700

# Articles
curl -s "http://localhost:1337/api/articles?filters[status][\$eq]=PUBLISHED&locale=fr&populate=*" | head -c 700
```

**Attendu** : Réponses JSON avec `data` non vide, pas d'erreur 403.

### 6.2 Tester le Frontend

1. Ouvrir : http://localhost:3000/offers/<OFFER_ID>
2. Vérifier :
   - ✅ Marketing sections affichent le contenu Strapi
   - ✅ Timeline affiche les OfferUpdates
   - ✅ Articles apparaissent (si créés)
   - ✅ Pas d'erreurs console
   - ✅ Pas de "Coming soon" partout

### 6.3 Vérifier les Variables d'Environnement

```bash
# Frontend-client doit avoir NEXT_PUBLIC_STRAPI_URL
docker compose -f docker-compose.dev.yml exec frontend-client sh -lc 'env | grep STRAPI'
# Doit afficher : NEXT_PUBLIC_STRAPI_URL=http://localhost:1337
```

Si manquant, redémarrer frontend-client après avoir vérifié docker-compose.dev.yml.

---

## Problèmes Courants

### Strapi ne démarre pas
- Vérifier les logs : `docker compose -f docker-compose.dev.yml logs cms-strapi`
- Vérifier que la DB `vancelian_cms` existe
- Vérifier les variables d'environnement dans `.env.dev`

### 403 sur les endpoints API
- Vérifier les permissions Public role (STEP 4)
- S'assurer que `find` et `findOne` sont activés

### Frontend n'affiche pas Strapi
- Vérifier NEXT_PUBLIC_STRAPI_URL dans les variables d'env
- Vérifier la console navigateur (erreurs CORS ?)
- Vérifier que le content type existe et est publié

### offer_id ne matche pas
- S'assurer que l'UUID dans Strapi correspond EXACTEMENT à celui de FastAPI
- Vérifier qu'il n'y a pas d'espaces avant/après l'UUID

---

## Prochaines Étapes Après Setup

Une fois tout validé :
1. ✅ Créer plus de contenu marketing
2. ✅ Migrer le contenu existant (si nécessaire)
3. ✅ Configurer R2/S3 pour les médias (optionnel)
4. ✅ Préparer le contenu multi-langue (en/it)



