# Guide de Création des Content Types Strapi

Ce guide décrit **étape par étape** comment créer les content types dans Strapi Admin.

## Prérequis

1. Strapi est démarré : `docker compose -f docker-compose.dev.yml up -d cms-strapi`
2. Accès admin : http://localhost:1337/admin
3. Compte admin créé (première connexion)

---

## Ordre de Création

**⚠️ IMPORTANT : Créer dans cet ordre** pour éviter les dépendances manquantes.

### 1. Single Type: Global

**Settings → Content-Type Builder → Single Types → Create new single type**

- **Display name**: `Global`
- **API ID (singular)**: `global`
- **API ID (plural)**: `globals`

**Fields à ajouter :**
1. `site_name` (Text, short text, required)
2. `site_tagline` (Text, short text)
3. `default_seo_title` (Text, short text)
4. `default_seo_description` (Text, long text)
5. `default_seo_image` (Media, single, image)
6. `social_links` (Component, repeatable) → Créer component "SocialLink" avec :
   - `platform` (Text, short text, required)
   - `url` (Text, short text, required)
7. `footer_legal` (Rich text)
8. `support_email` (Email)

**i18n** : ✅ Cocher "Enable localization for this Content-Type"

**Save**

---

### 2. Collection Type: Page

**Settings → Content-Type Builder → Collection Types → Create new collection type**

- **Display name**: `Page`
- **API ID (singular)**: `page`
- **API ID (plural)**: `pages`

**Fields à ajouter :**
1. `slug` (UID, based on: title, required, unique)
2. `title` (Text, short text, required)
3. `subtitle` (Text, short text)
4. `content` (Rich text ou Textarea pour markdown)
5. `hero_image` (Media, single, image)
6. `seo_title` (Text, short text)
7. `seo_description` (Text, long text)
8. `seo_image` (Media, single, image)

**i18n** : ✅ Cocher "Enable localization"

**Save**

---

### 3. Collection Type: OfferMarketing

**Settings → Content-Type Builder → Collection Types → Create new collection type**

- **Display name**: `Offer Marketing`
- **API ID (singular)**: `offer-marketing`
- **API ID (plural)**: `offer-marketings`

**Fields à ajouter :**
1. `offer_id` (Text, short text, required, unique) - UUID depuis FastAPI
2. `title` (Text, short text)
3. `subtitle` (Text, short text)
4. `location` (Text, short text)
5. `highlights` (JSON, ou Repeatable Text) - Liste de highlights
6. `why_invest` (Component, repeatable) → Créer component "WhyInvestItem" avec :
   - `title` (Text, short text, required)
   - `text` (Text, long text)
   - `icon` (Text, short text, optional)
7. `metrics` (Component, single) → Créer component "Metrics" avec :
   - `target_yield` (Number, decimal)
   - `investors_count` (Number, integer)
   - `days_left` (Number, integer)
8. `breakdown` (Component, single) → Créer component "Breakdown" avec :
   - `purchase_cost` (Number, decimal)
   - `transaction_cost` (Number, decimal)
   - `running_cost` (Number, decimal)
   - `currency` (Text, short text)
9. `cover_image` (Media, single, image)
10. `gallery` (Media, multiple, images)
11. `promo_video` (Media, single, video)
12. `documents` (Media, multiple, files)

**i18n** : ✅ Cocher "Enable localization"

**Save**

---

### 4. Collection Type: OfferUpdate

**Settings → Content-Type Builder → Collection Types → Create new collection type**

- **Display name**: `Offer Update`
- **API ID (singular)**: `offer-update`
- **API ID (plural)**: `offer-updates`

**Fields à ajouter :**
1. `offer_id` (Text, short text, required) - UUID depuis FastAPI, **indexé**
2. `title` (Text, short text, required)
3. `description` (Text, long text, max ~300 chars recommandé)
4. `date` (Date, date time, required)
5. `status` (Enumeration) :
   - `INFO`
   - `MILESTONE`
   - `SUCCESS`
   - `WARNING`
6. `article_slug` (Text, short text, optional) - Slug d'article blog si lié
7. `media` (Media, multiple, images/video)

**i18n** : ✅ Cocher "Enable localization"

**Settings par défaut** :
- Default sort: `date:desc`

**Save**

---

### 5. Collection Type: Partner

**Settings → Content-Type Builder → Collection Types → Create new collection type**

- **Display name**: `Partner`
- **API ID (singular)**: `partner`
- **API ID (plural)**: `partners`

**Fields à ajouter :**
1. `slug` (UID, based on: name, required, unique)
2. `name` (Text, short text, required)
3. `legal_name` (Text, short text)
4. `website` (Text, short text)
5. `country` (Text, short text)
6. `city` (Text, short text)
7. `description` (Rich text)
8. `logo` (Media, single, image)
9. `cover_image` (Media, single, image)
10. `ceo_name` (Text, short text)
11. `ceo_title` (Text, short text)
12. `ceo_photo` (Media, single, image)
13. `ceo_message_quote` (Text, short text)
14. `ceo_bio_markdown` (Rich text ou Textarea)
15. `videos` (Media, multiple, videos)
16. `documents` (Media, multiple, files)

**i18n** : ✅ Cocher "Enable localization"

**Save**

---

### 6. Collection Type: PartnerProject

**Settings → Content-Type Builder → Collection Types → Create new collection type**

- **Display name**: `Partner Project`
- **API ID (singular)**: `partner-project`
- **API ID (plural)**: `partner-projects`

**Fields à ajouter :**
1. `partner` (Relation, many-to-one, Partner, required)
2. `title` (Text, short text, required)
3. `location` (Text, short text)
4. `year` (Number, integer)
5. `summary` (Text, long text)
6. `results` (Text, long text)
7. `cover_image` (Media, single, image)
8. `gallery` (Media, multiple, images)
9. `video` (Media, single, video, optional)
10. `document` (Media, single, file, optional)

**i18n** : ✅ Cocher "Enable localization"

**Save**

---

### 7. Collection Type: Article

**Settings → Content-Type Builder → Collection Types → Create new collection type**

- **Display name**: `Article`
- **API ID (singular)**: `article`
- **API ID (plural)**: `articles`

**Fields à ajouter :**
1. `slug` (UID, based on: title, required, unique)
2. `title` (Text, short text, required)
3. `excerpt` (Text, long text)
4. `content_markdown` (Rich text ou Textarea pour markdown)
5. `cover_image` (Media, single, image)
6. `gallery` (Media, multiple, images)
7. `promo_video` (Media, single, video, optional)
8. `published_at` (Date, date time)
9. `status` (Enumeration) :
   - `DRAFT`
   - `PUBLISHED`
10. `related_offer_ids` (JSON, ou Repeatable Text) - Liste UUIDs offers FastAPI
11. `tags` (Text, repeatable)

**i18n** : ✅ Cocher "Enable localization"

**Save**

---

## Configuration des Permissions API

**Settings → Users & Permissions → Roles → Public**

Activer **uniquement** les permissions suivantes pour chaque content type :

### Global
- ✅ `find`

### Page
- ✅ `find`
- ✅ `findOne`

### Offer Marketing
- ✅ `find`
- ✅ `findOne`

### Offer Update
- ✅ `find`
- ✅ `findOne`

### Partner
- ✅ `find`
- ✅ `findOne`

### Partner Project
- ✅ `find`
- ✅ `findOne`

### Article
- ✅ `find`
- ✅ `findOne`

**⚠️ IMPORTANT** :
- ❌ Ne PAS activer `create`, `update`, `delete` sur Public
- ❌ Ne PAS activer `upload` sur Public

**Save**

---

## Vérification

### Test API Endpoints

Une fois les content types créés et les permissions configurées, tester :

```bash
# Global
curl http://localhost:1337/api/global?locale=fr

# Pages
curl http://localhost:1337/api/pages?locale=fr

# Offer Marketing (remplacer UUID)
curl "http://localhost:1337/api/offer-marketings?filters[offer_id][\$eq]=<uuid>&locale=fr&populate=*"

# Offer Updates
curl "http://localhost:1337/api/offer-updates?filters[offer_id][\$eq]=<uuid>&locale=fr&sort=date:desc&populate=*"

# Articles
curl "http://localhost:1337/api/articles?filters[status][\$eq]=PUBLISHED&locale=fr&populate=*"

# Partners
curl "http://localhost:1337/api/partners?locale=fr&populate=*"
```

Tous doivent retourner `200 OK` avec des données JSON (même si vides).

---

## Notes

- Les content types sont créés via l'interface Strapi (pas de code)
- FastAPI reste source de vérité pour les données business (investments, transactions)
- Strapi gère uniquement le contenu marketing/presentation
- Le lien se fait via `offer_id` (UUID string) - pas de foreign key



