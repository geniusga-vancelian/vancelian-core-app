# Sandbox Demo20 React Integration

Guide d'intégration du template Sandbox `demo20.html` dans Next.js avec des composants React réutilisables.

## Structure

### Layout et Page

- **`frontend-client/app/(marketing)/demo20/layout.tsx`** : Layout dédié qui charge les CSS/JS du thème Sandbox
- **`frontend-client/app/(marketing)/demo20/page.tsx`** : Page principale qui assemble les composants
- **`frontend-client/app/(marketing)/demo20/Demo20Head.tsx`** : Composant client pour injecter les CSS dans le `<head>`

### Composants

Tous les composants sont dans `frontend-client/components/sandbox/demo20/` :

- **`HeaderNav.tsx`** : Navigation header (version simplifiée, peut être étendue)
- **`HeroVideo.tsx`** : Hero section avec vidéo en arrière-plan
- **`SectionServices.tsx`** : Section services (structure de base)
- **`SectionProcess.tsx`** : Section processus de travail
- **`SectionProjects.tsx`** : Section portfolio/projets
- **`SectionClients.tsx`** : Section clients/logo cloud
- **`SectionCTA.tsx`** : Section call-to-action avec vidéo et features
- **`Footer.tsx`** : Footer

## Chargement des Assets

### CSS

Les CSS sont chargés via `Demo20Head.tsx` (client-side) :

- `/theme/assets/fonts/unicons/unicons.css`
- `/theme/assets/css/plugins.css`
- `/theme/style.css`
- `/theme/assets/css/colors/purple.css`
- `/theme/assets/css/fonts/urbanist.css`

### JavaScript

Les scripts sont chargés via `next/script` dans le layout :

- `/theme/assets/js/plugins.js` (strategy: `afterInteractive`)
- `/theme/assets/js/theme.js` (strategy: `afterInteractive`)

### Protection JS Init

La page `page.tsx` contient un `useEffect` qui :
- Vérifie que le thème n'est pas déjà initialisé (`__demo20_theme_inited`)
- Appelle `window.theme.init()` si disponible
- Gère les erreurs silencieusement

## Utilisation

### Route

La page est accessible via : `http://localhost:3000/demo20`

### Comparaison avec le template original

Template statique : `http://localhost:3000/theme/demo20.html`
Page React : `http://localhost:3000/demo20`

Les deux doivent avoir un rendu visuellement similaire.

## État actuel

### ✅ Implémenté

- Structure de base de la page
- Layout avec chargement CSS/JS
- Composants de base (structure HTML identique au template)
- Protection contre double init JS
- Chemin des assets remappés vers `/theme/assets/...`

### 🔄 À compléter

Les composants sont actuellement des stubs avec la structure de base. Pour une implémentation complète, il faudrait :

1. **HeaderNav** : Ajouter les menus déroulants complets (Demos, Pages, Projects, Blog, Blocks, Documentation)
2. **SectionServices** : Ajouter les 3 services (Web Design, Mobile Development, SEO Optimization) avec images et listes
3. **SectionProcess** : Ajouter les 3 étapes du processus avec icônes SVG
4. **SectionProjects** : Ajouter la grille de projets avec lightbox
5. **SectionClients** : Ajouter la grille de logos clients
6. **SectionCTA** : Ajouter la vidéo, les 4 features et les statistiques
7. **Footer** : Compléter avec toutes les colonnes et le formulaire newsletter

## Tests

### Tests manuels

1. **Vérifier le rendu** :
   ```bash
   npm run dev
   # Ouvrir http://localhost:3000/demo20
   # Comparer avec http://localhost:3000/theme/demo20.html
   ```

2. **Vérifier les assets** :
   - Onglet Network : 0 x 404 sur CSS/JS/img/media
   - Console : pas d'erreur runtime (warnings OK)

3. **Vérifier les interactions** :
   - Menu mobile (hamburger) fonctionne
   - Dropdowns fonctionnent (si Bootstrap chargé)
   - Vidéo hero se joue en auto

## Notes techniques

- Les classes Tailwind du template sont préservées
- Les chemins d'assets utilisent `/theme/assets/...` (public folder)
- Les liens internes utilisent `next/link`, les liens externes utilisent `<a>`
- Le layout utilise `page-frame !bg-[#e0e9fa]` comme wrapper global (de demo20.html)

## Problèmes connus

- Les composants sont des stubs : le contenu complet doit être ajouté progressivement
- Le header est simplifié : les mega-menus complets ne sont pas implémentés
- Certaines animations/JS du template peuvent nécessiter des ajustements pour fonctionner avec React


