# Strapi/Frontend Compatibility Fixes

## Résumé des Corrections

### 1. UIDs de Composants Corrigés

**Avant :**
- `marketing.marketing-hero`
- `marketing.marketing-header-nav`

**Après :**
- `marketing.hero` ✅
- `marketing.header-nav` ✅

**Fichiers créés :**
- `cms-strapi/src/components/marketing/hero.json` (nouveau schéma avec UID correct)
- `cms-strapi/src/components/marketing/header-nav.json` (nouveau schéma avec UID correct)

**Migration :**
- Les anciens UIDs (`marketing.marketing-hero`, `marketing.marketing-header-nav`) sont toujours acceptés dans `Page.schema.json` pour compatibilité
- Le frontend utilise `normalizeComponentUid()` pour gérer les deux formats
- **Action requise :** Dans Strapi Admin, ré-enregistrer les pages existantes en utilisant les nouveaux composants `hero` et `header-nav`

### 2. Noms de Champs Corrigés

#### Hero (`marketing.hero`)
- ✅ Ajout de `backgroundImage` (en plus de `background_image` existant)
- ✅ Ajout de `primaryCtaLabel`, `primaryCtaHref`, `secondaryCtaLabel`, `secondaryCtaHref` (champs plats)
- ✅ Conservation de `primary_cta`, `secondary_cta` (components) pour compatibilité
- **Frontend :** Utilise les nouveaux champs avec fallback sur les anciens

#### HeaderNav (`marketing.header-nav`)
- ✅ Ajout de `logo_href` (default: "/p/home")
- ✅ Ajout de `cta_label`, `cta_href`, `cta_variant` (champs plats)
- ✅ Conservation de `primary_cta` (component) pour compatibilité
- **Frontend :** Utilise les nouveaux champs avec fallback sur `primary_cta` component

#### FeatureGrid (`marketing.feature-grid`)
- ✅ Ajout de `items` (en plus de `features` existant)
- **Frontend :** Utilise `items` avec fallback sur `features`

#### CTA (`marketing.cta`)
- ✅ Ajout de `subtitle` (en plus de `description` existant)
- ✅ Ajout de `ctaLabel`, `ctaHref` (champs plats)
- ✅ Conservation de `cta` (component) et `description` pour compatibilité
- **Frontend :** Utilise `subtitle` avec fallback sur `description`, et `ctaLabel`/`ctaHref` avec fallback sur `cta` component

#### Footer (`marketing.footer-simple`)
- ✅ Ajout de `copyrightText` (en plus de `copyright` existant)
- **Frontend :** Utilise `copyrightText` avec fallback sur `copyright`

## Checklist de Vérification

### 1. Redémarrer Strapi
```bash
cd cms-strapi
npm run develop
# ou
docker compose -f docker-compose.dev.yml restart cms-strapi
```

### 2. Vérifier les Composants dans Strapi Admin
- Aller dans **Content-Type Builder** → **Components**
- Vérifier que les composants suivants existent :
  - ✅ `marketing.hero` (nouveau)
  - ✅ `marketing.header-nav` (nouveau)
  - ✅ `marketing.feature-grid`
  - ✅ `marketing.cta`
  - ✅ `marketing.footer-simple`
  - ⚠️ `marketing.marketing-hero` (ancien, peut être supprimé après migration)
  - ⚠️ `marketing.marketing-header-nav` (ancien, peut être supprimé après migration)

### 3. Vérifier le Schema Page
```bash
# Vérifier que Page.sections inclut les bons UIDs
cat cms-strapi/src/api/page/content-types/page/schema.json | grep -A 10 "dynamiczone"
```
**Attendu :**
```json
"components": [
  "marketing.hero",
  "marketing.header-nav",
  "marketing.feature-grid",
  "marketing.cta",
  "marketing.footer-simple",
  "marketing.marketing-hero",  // ancien, pour compatibilité
  "marketing.marketing-header-nav"  // ancien, pour compatibilité
]
```

### 4. Tester l'API Strapi
```bash
curl "http://localhost:1337/api/pages?filters[slug][\$eq]=home&locale=en&populate[sections]=deep" | jq '.data[0].attributes.sections[] | {__component, title}'
```

**Résultat attendu :**
- Les sections doivent avoir `__component: "marketing.hero"` ou `"marketing.header-nav"` (pas `marketing.marketing-hero`)
- Les champs doivent être présents (avec les nouveaux noms si utilisés)

### 5. Tester le Frontend
```bash
cd frontend-client
npm run dev
# Ouvrir http://localhost:3000/p/home?locale=en
```

**Vérifications :**
- ✅ La page s'affiche sans erreur
- ✅ Les blocs sont rendus correctement
- ✅ Console browser : pas d'erreur, logs de debug montrent les UIDs normalisés
- ✅ Network tab : pas de 404

### 6. Migration du Contenu Existant (si nécessaire)

Si vous avez du contenu existant utilisant les anciens UIDs :

1. **Dans Strapi Admin :**
   - Aller dans **Content Manager** → **Page**
   - Ouvrir chaque page
   - Pour chaque section utilisant `marketing.marketing-hero` ou `marketing.marketing-header-nav` :
     - Supprimer la section
     - Ajouter une nouvelle section avec le composant `hero` ou `header-nav`
     - Recopier les données
     - Sauvegarder

2. **Alternative (si beaucoup de contenu) :**
   - Laisser les anciens composants actifs
   - Le frontend gère les deux formats via `normalizeComponentUid()`
   - Migrer progressivement

## Notes Techniques

### Support des Deux Formats

Le frontend utilise maintenant des fallbacks pour supporter à la fois :
- Les nouveaux champs (camelCase pour Hero, snake_case pour les autres)
- Les anciens champs (snake_case, components)

### Extraction des CTA Components

Quand un CTA est stocké comme component (`primary_cta`, `secondary_cta`), le frontend extrait automatiquement `label` et `href` :
```typescript
const primaryCta = Array.isArray(section.primary_cta) && section.primary_cta.length > 0 
  ? section.primary_cta[0] 
  : null;
primaryCtaLabel={section.primaryCtaLabel || primaryCta?.label || undefined}
```

## Prochaines Étapes (Optionnel)

1. **Supprimer les anciens composants** (`marketing.marketing-hero`, `marketing.marketing-header-nav`) après migration complète du contenu
2. **Unifier les noms de champs** : choisir soit camelCase soit snake_case et migrer progressivement
3. **Ajouter les composants manquants** : `stats-strip`, `logo-cloud`, `testimonials`, `portfolio-grid` (déjà dans la doc mais pas encore créés)


