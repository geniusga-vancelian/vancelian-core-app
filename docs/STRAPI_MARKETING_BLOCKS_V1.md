# Strapi Marketing Blocks V1 - Setup Guide

Guide pour créer les composants marketing et le Content Type Page avec Dynamic Zone dans Strapi.

## Architecture

- **Content Type**: `Page` avec Dynamic Zone `sections`
- **Composants**: 9 blocs marketing réutilisables (V1.1 + V1.2)
- **Routes Frontend**:
  - `/site?slug=home&locale=fr` (originale, backward compatible)
  - `/p/home?locale=fr` (route friendly, recommandée)
- **Layout**: Layout dédié pour routes marketing (sans TopBar/DevBanner)
- **Multi-langue**: i18n activé (fr/en/it)

---

## 1. Créer les Composants Marketing

Dans **Strapi Admin** → **Settings** → **Content-Type Builder** → **Components**

### A. Component: `marketing.hero`

**Create a new component** → **Single component**

- **Category**: `marketing` (créer cette catégorie si elle n'existe pas)
- **Display name**: `Hero`
- **API ID**: `hero`

**Fields**:
1. `title` (Text, short text, **required**)
2. `subtitle` (Text, long text)
3. `primaryCtaLabel` (Text, short text)
4. `primaryCtaHref` (Text, short text)
5. `secondaryCtaLabel` (Text, short text)
6. `secondaryCtaHref` (Text, short text)
7. `backgroundImage` (Media, single, **images only**)

**Save**

---

### B. Component: `marketing.feature-item`

**Create a new component** → **Single component**

- **Category**: `marketing`
- **Display name**: `Feature Item`
- **API ID**: `feature-item`

**Fields**:
1. `title` (Text, short text, **required**)
2. `description` (Text, long text)
3. `icon` (Text, short text) - Ex: "shield", "chart", "sparkles"

**Save**

---

### C. Component: `marketing.feature-grid`

**Create a new component** → **Single component**

- **Category**: `marketing`
- **Display name**: `Feature Grid`
- **API ID**: `feature-grid`

**Fields**:
1. `title` (Text, short text)
2. `items` (Component, **repeatable**, min: 1, max: 12)
   - Sélectionner: `marketing.feature-item`

**Save**

---

### D. Component: `marketing.link`

**Create a new component** → **Single component**

- **Category**: `marketing`
- **Display name**: `Link`
- **API ID**: `link`

**Fields**:
1. `label` (Text, short text, **required**)
2. `href` (Text, short text, **required**)

**Save**

---

### E. Component: `marketing.cta`

**Create a new component** → **Single component**

- **Category**: `marketing`
- **Display name**: `CTA`
- **API ID**: `cta`

**Fields**:
1. `title` (Text, short text, **required**)
2. `subtitle` (Text, long text)
3. `ctaLabel` (Text, short text)
4. `ctaHref` (Text, short text)

**Save**

---

### F. Component: `marketing.footer-simple`

**Create a new component** → **Single component**

- **Category**: `marketing`
- **Display name**: `Footer Simple`
- **API ID**: `footer-simple`

**Fields**:
1. `copyrightText` (Text, short text)
2. `links` (Component, **repeatable**, max: 10)
   - Sélectionner: `marketing.link`

**Save**

---

## V1.1 - Marketing Site Layout & Header Navigation

### Layout Marketing Dédié

Les pages sous `/site` et `/p/[slug]` utilisent maintenant un layout dédié (`app/(marketing)/layout.tsx`) qui :
- ❌ N'affiche **pas** la `TopBar` Vancelian
- ❌ N'affiche **pas** le `DevBanner`
- ✅ Affiche uniquement le contenu de la page (header-nav, hero, etc.)

Cela permet de créer des sites vitrine complets directement depuis Strapi.

### Routes Disponibles

- `/site?slug=home&locale=fr` (route originale, backward compatible)
- `/p/home?locale=fr` (route friendly, recommandée)

Les deux routes utilisent le même rendu et supportent le SEO via `generateMetadata()`.

---

## V1.2 - Header Navigation Block (Enhanced)

### Nouveau composant: `marketing.header-nav`

**Create a new component** → **Single component**

- **Category**: `marketing`
- **Display name**: `Header Nav`
- **API ID**: `header-nav`

**Fields**:
1. `logo_text` (Text, short text, default: "Vancelian") - Texte du logo si pas d'image
2. `logo_href` (Text, short text, default: "/site?slug=home") - URL du logo
3. `logo` (Media, single, **images only**) - Image du logo (optionnel)
4. `links` (Component, **repeatable**)
   - Sélectionner: `marketing.link` (déjà créé)
   - Chaque lien a: `label`, `href`, `is_external` (boolean)
5. `cta_label` (Text, short text) - Label du bouton CTA
6. `cta_href` (Text, short text) - URL du bouton CTA
7. `cta_variant` (Enum, default: "primary") - Options: "primary" | "secondary"
8. `sticky` (Boolean, default: `true`) - Header fixe en haut lors du scroll
9. `transparent_on_top` (Boolean, default: `false`) - Header transparent au top, devient opaque au scroll
10. `theme` (Enum, default: "light") - Options: "light" | "dark"

**Save**

### Utilisation dans Dynamic Zone

Dans le Content Type `Page`, ajouter `marketing.header-nav` aux composants autorisés dans la Dynamic Zone `sections`.

**Ordre recommandé** :
1. `marketing.header-nav` (toujours en premier)
2. `marketing.hero`
3. `marketing.feature-grid`
4. `marketing.cta`
5. `marketing.footer-simple` (toujours en dernier)

**Note**: Si vous utilisez `transparent_on_top=true` sur le header, placez le hero juste après pour un effet de superposition élégant.

### Fonctionnalités du HeaderNav

- **Responsive**: Menu hamburger sur mobile avec slide-over panel
- **Sticky**: Option pour fixer le header en haut au scroll
- **Transparent mode**: Si `transparent_on_top=true`, le header est transparent au top et devient opaque après scroll
- **Theme**: Support light/dark avec classes Tailwind adaptées
- **CTA**: Bouton CTA avec variants primary/secondary
- **External links**: Support des liens externes (nouvel onglet)

---

## V1.2 - Additional Marketing Blocks (Stats, Logos, Testimonials, Portfolio)

### G. Component: `marketing.stat-item`

**Create a new component** → **Single component**

- **Category**: `marketing`
- **Display name**: `Stat Item`
- **API ID**: `stat-item`

**Fields**:
1. `label` (Text, short text, **required**)
2. `value` (Text, short text, **required**)
3. `hint` (Text, short text) - Texte d'aide optionnel
4. `icon` (Text, short text) - Nom d'icône (ex: "sparkles", "shield")

**Save**

---

### H. Component: `marketing.stats-strip`

**Create a new component** → **Single component**

- **Category**: `marketing`
- **Display name**: `Stats Strip`
- **API ID**: `stats-strip`

**Fields**:
1. `title` (Text, short text)
2. `items` (Component, **repeatable**, min: 1, max: 6)
   - Sélectionner: `marketing.stat-item`
3. `variant` (Enum, default: "carded") - Options: "plain" | "carded"

**Save**

---

### I. Component: `marketing.logo-item`

**Create a new component** → **Single component**

- **Category**: `marketing`
- **Display name**: `Logo Item`
- **API ID**: `logo-item`

**Fields**:
1. `name` (Text, short text, **required**)
2. `logo` (Media, single, **images only**, **required**)
3. `href` (Text, short text) - URL optionnelle
4. `dark_logo` (Media, single, **images only**) - Logo pour thème sombre

**Save**

---

### J. Component: `marketing.logo-cloud`

**Create a new component** → **Single component**

- **Category**: `marketing`
- **Display name**: `Logo Cloud`
- **API ID**: `logo-cloud`

**Fields**:
1. `title` (Text, short text)
2. `items` (Component, **repeatable**, max: 20)
   - Sélectionner: `marketing.logo-item`
3. `variant` (Enum, default: "grid") - Options: "grid" | "carousel"

**Save**

---

### K. Component: `marketing.testimonial`

**Create a new component** → **Single component**

- **Category**: `marketing`
- **Display name**: `Testimonial`
- **API ID**: `testimonial`

**Fields**:
1. `quote` (Text, long text, **required**, max ~280 caractères)
2. `author_name` (Text, short text, **required**)
3. `author_title` (Text, short text) - Titre/position de l'auteur
4. `author_avatar` (Media, single, **images only**)
5. `company` (Text, short text) - Nom de l'entreprise
6. `rating` (Integer) - Note de 1 à 5 (optionnel)

**Save**

---

### L. Component: `marketing.testimonials`

**Create a new component** → **Single component**

- **Category**: `marketing`
- **Display name**: `Testimonials`
- **API ID**: `testimonials`

**Fields**:
1. `title` (Text, short text)
2. `subtitle` (Text, long text)
3. `items` (Component, **repeatable**, max: 12)
   - Sélectionner: `marketing.testimonial`
4. `variant` (Enum, default: "slider") - Options: "grid" | "slider"
5. `auto_advance` (Boolean, default: false) - Défilement automatique
6. `interval_ms` (Integer, default: 6000) - Intervalle en millisecondes (si auto_advance true)

**Save**

---

### M. Component: `marketing.portfolio-item`

**Create a new component** → **Single component**

- **Category**: `marketing`
- **Display name**: `Portfolio Item`
- **API ID**: `portfolio-item`

**Fields**:
1. `title` (Text, short text, **required**)
2. `subtitle` (Text, short text)
3. `cover_image` (Media, single, **images only**, **required**)
4. `href` (Text, short text) - URL optionnelle
5. `tags` (JSON) - Array de strings (ex: `["Web", "Mobile", "Design"]`)
6. `location` (Text, short text)
7. `year` (Text, short text)

**Save**

---

### N. Component: `marketing.portfolio-grid`

**Create a new component** → **Single component**

- **Category**: `marketing`
- **Display name**: `Portfolio Grid`
- **API ID**: `portfolio-grid`

**Fields**:
1. `title` (Text, short text)
2. `subtitle` (Text, long text)
3. `items` (Component, **repeatable**, max: 30)
   - Sélectionner: `marketing.portfolio-item`
4. `columns` (Enum, default: "3") - Options: "2" | "3" | "4"
5. `show_filters` (Boolean, default: false) - Afficher les filtres par tags

**Save**

---

## 2. Mettre à jour le Content Type `Page`

Dans **Strapi Admin** → **Settings** → **Content-Type Builder** → **Collection Types** → **Page**

### Ajouter Dynamic Zone

1. Cliquer sur **Add another field**
2. Sélectionner **Dynamic Zone**
3. **Display name**: `sections`
4. **API ID**: `sections`

**Composants autorisés dans la Dynamic Zone** (V1.1 + V1.2):
- ✅ `marketing.header-nav`
- ✅ `marketing.hero`
- ✅ `marketing.feature-grid`
- ✅ `marketing.cta`
- ✅ `marketing.footer-simple`
- ✅ `marketing.stats-strip` (V1.2)
- ✅ `marketing.logo-cloud` (V1.2)
- ✅ `marketing.testimonials` (V1.2)
- ✅ `marketing.portfolio-grid` (V1.2)

**Save**

### Vérifier les autres champs

Assurez-vous que `Page` a aussi :
- `title` (Text, required)
- `slug` (UID, based on title, required, unique)
- `seo_title` (Text)
- `seo_description` (Text, long text)
- `seo_image` (Media, single, image)
- `is_published` (Boolean) OU utiliser le publication workflow Strapi (publishedAt)

**i18n** : ✅ Doit être activé pour `Page`

---

## 3. Configurer les Permissions Publiques

**Settings** → **Users & Permissions** → **Roles** → **Public**

Pour le Content Type `Page` :
- ✅ `find` (GET /api/pages)
- ✅ `findOne` (GET /api/pages/:id)
- ❌ `create`, `update`, `delete`, `upload` (désactivés)

**Save**

---

## 4. Créer une Page "Home" de Test

**Content Manager** → **Page** → **Create new entry**

**Locale**: `fr` (ou la locale par défaut)

**Fields**:
- `title`: "Home"
- `slug`: "home" (auto-généré depuis title)
- `seo_title`: "Vancelian - Home"
- `seo_description`: "Bienvenue sur Vancelian"

**Sections** (Dynamic Zone) - Ordre recommandé :
1. **Ajouter** → `marketing.header-nav`
   - Configurer logo, liens, CTA

2. **Ajouter** → `marketing.hero`
   - `title`: "Bienvenue sur Vancelian"
   - `subtitle`: "La plateforme d'investissement immobilier nouvelle génération"
   - `primaryCtaLabel`: "Découvrir les offres"
   - `primaryCtaHref`: "/offers"
   - `backgroundImage`: Uploader une image

3. **Ajouter** → `marketing.stats-strip` (V1.2)
   - `title`: "Nos chiffres"
   - `variant`: "carded"
   - `items`: 3-4 stat-items avec valeurs et labels

4. **Ajouter** → `marketing.logo-cloud` (V1.2)
   - `title`: "Ils nous font confiance"
   - `variant`: "grid"
   - `items`: Logo items avec images

5. **Ajouter** → `marketing.feature-grid`
   - `title`: "Nos avantages"
   - `items` (2-3 items):
     - Item 1:
       - `title`: "Investissement sécurisé"
       - `description`: "Protection de votre capital"
       - `icon`: "shield"
     - Item 2:
       - `title`: "Rendements attractifs"
       - `description`: "Des retours sur investissement compétitifs"
       - `icon`: "chart"

6. **Ajouter** → `marketing.portfolio-grid` (V1.2)
   - `title`: "Nos réalisations"
   - `items`: Portfolio items avec images, titres, tags
   - `show_filters`: true (pour activer les filtres)

7. **Ajouter** → `marketing.testimonials` (V1.2)
   - `title`: "Ils parlent de nous"
   - `variant`: "slider"
   - `items`: Testimonials avec quotes, auteurs, avatars
   - `auto_advance`: true (optionnel)

8. **Ajouter** → `marketing.cta`
   - `title`: "Prêt à commencer ?"
   - `subtitle`: "Rejoignez des milliers d'investisseurs"
   - `ctaLabel`: "Créer un compte"
   - `ctaHref`: "/register"

9. **Ajouter** → `marketing.footer-simple`
   - `copyrightText`: "© 2024 Vancelian. Tous droits réservés."
   - `links`:
     - Link 1: `label`="Mentions légales", `href`="/legal"
     - Link 2: `label`="Contact", `href`="/contact"

**Save** → **Publish**

---

## 5. Tester l'API

```bash
# Tester la récupération de la page "home"
curl -s "http://localhost:1337/api/pages?filters[slug][\$eq]=home&locale=fr&populate=deep" | jq '.data[0].attributes.sections'
```

**Attendu** : Un array de sections avec `__component` et les données de chaque bloc.

---

## 6. Tester le Frontend Marketing Site

1. Ouvrir : http://localhost:3000/p/home?locale=fr (ou /site?slug=home&locale=fr)
2. Vérifier :
   - ✅ Pas de TopBar/DevBanner Vancelian
   - ✅ Header navigation s'affiche (si présent dans sections)
   - ✅ Toutes les sections s'affichent dans l'ordre
   - ✅ StatsStrip affiche les statistiques
   - ✅ LogoCloud affiche les logos (grid ou carousel)
   - ✅ Testimonials slider fonctionne (prev/next + auto-advance si activé)
   - ✅ PortfolioGrid affiche les items avec filtres si activés
   - ✅ Menu hamburger fonctionne sur mobile
   - ✅ Liens naviguent correctement (interne/externe)
   - ✅ Images se chargent correctement
   - ✅ Pas d'erreurs console
   - ✅ SEO metadata correcte (inspecter <head>)

### 6.3 Tester le Frontend Offers (existant)

1. Ouvrir : http://localhost:3000/offers/<OFFER_ID>
2. Vérifier :
   - ✅ Marketing sections affichent le contenu Strapi
   - ✅ Timeline affiche les OfferUpdates
   - ✅ Articles apparaissent (si créés)
   - ✅ Pas d'erreurs console
   - ✅ Pas de "Coming soon" partout

---

## Notes Techniques

### Structure de la réponse Strapi

```json
{
  "data": [{
    "attributes": {
      "title": "Home",
      "slug": "home",
      "sections": [
        {
          "__component": "marketing.header-nav",
          "logo_text": "Vancelian",
          "links": [ ... ]
        },
        {
          "__component": "marketing.hero",
          "title": "...",
          "subtitle": "...",
          "backgroundImage": { ... }
        },
        {
          "__component": "marketing.stats-strip",
          "title": "...",
          "items": [ ... ]
        }
      ]
    }
  }]
}
```

### Mapping Frontend

- `marketing.header-nav` → `<HeaderNavBlock />` (V1.1+)
- `marketing.hero` → `<HeroBlock />`
- `marketing.feature-grid` → `<FeatureGridBlock />`
- `marketing.cta` → `<CtaBlock />`
- `marketing.footer-simple` → `<FooterSimpleBlock />`
- `marketing.stats-strip` → `<StatsStripBlock />` (V1.2)
- `marketing.logo-cloud` → `<LogoCloudBlock />` (V1.2)
- `marketing.testimonials` → `<TestimonialsBlock />` (V1.2)
- `marketing.portfolio-grid` → `<PortfolioGridBlock />` (V1.2)
- Bloc inconnu → `<UnsupportedBlock />` (fallback en dev seulement)

### Résolution des URLs Media

Les composants utilisent `getMediaUrl()` et `getStrapiBaseUrl()` pour résoudre les URLs relatives en URLs absolues :
- Si l'URL commence par `http`, elle est utilisée telle quelle
- Sinon, elle est préfixée avec la base URL Strapi

---

## Troubleshooting

### Les sections ne s'affichent pas
- Vérifier que `populate=deep` est utilisé dans l'API call
- Vérifier les permissions Public sur `Page`
- Vérifier que la page est **publiée**

### Erreur "Unsupported block"
- Vérifier que `__component` correspond exactement aux noms ci-dessus
- Vérifier le mapping dans `StrapiSectionsRenderer.tsx`

### Images ne s'affichent pas
- Vérifier que les médias sont uploadés dans Strapi
- Vérifier que `getMediaUrl()` dans `cms.ts` fonctionne
- Vérifier les permissions Public sur `Media` (Settings → Users & Permissions → Roles → Public → Media → `find`)

### Testimonials slider ne fonctionne pas
- Vérifier que `variant="slider"` est défini
- Vérifier la console pour les erreurs JavaScript
- Vérifier que `auto_advance` et `interval_ms` sont correctement configurés

### Portfolio filters ne fonctionnent pas
- Vérifier que `show_filters=true` est activé
- Vérifier que les items ont des `tags` (format JSON array ou string)
- Vérifier la console pour les erreurs JavaScript

---

## Prochaines Étapes (V3+)

- Plus de blocs (FAQ, Pricing, Team, etc.)
- Réutiliser les blocs existants du template sandbox
- A/B testing de sections
- Preview mode pour les admins
- Animations et transitions avancées
