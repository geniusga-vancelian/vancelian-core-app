# Theme Sandbox Runbook

Guide pour utiliser le template Sandbox dans l'application Vancelian.

## Architecture

### Structure des fichiers

```
frontend-client/
├── theme/
│   └── source/
│       └── dist/           # Source vendor (ne pas modifier directement)
│           ├── *.html
│           └── assets/
├── public/
│   └── theme/              # Source de vérité runtime (généré par theme:sync)
│       ├── *.html          # Fichiers HTML copiés
│       ├── assets/         # Assets copiés
│       └── index.json      # Index généré
└── scripts/
    └── theme-sync.mjs      # Script de synchronisation
```

### Pourquoi iframe ?

Le preview utilise un **iframe** au lieu de parser/injecter le HTML pour garantir :

1. **Fidélité 100%** : Le template s'affiche exactement comme dans `/theme/demo1.html`
2. **Isolation complète** : Aucun conflit CSS/JS avec Next.js ou Tailwind global
3. **Simplicité** : Pas de parsing complexe, pas de gestion d'erreurs JS template
4. **Fiabilité** : Le template fonctionne dans son propre contexte, comme prévu

### Flux de synchronisation

```
theme/source/dist/  →  (npm run theme:sync)  →  public/theme/
```

Le script `theme-sync.mjs` :
- Copie tous les `*.html` de `theme/source/dist/` vers `public/theme/`
- Copie `theme/source/dist/assets/` vers `public/theme/assets/`
- Génère `public/theme/index.json` avec la liste des fichiers

## Installation

### 1. Copier le template source

Placez les fichiers du template Sandbox dans :

```
frontend-client/theme/source/dist/
├── demo1.html
├── demo2.html
├── ...
└── assets/
    ├── css/
    ├── js/
    ├── img/
    └── ...
```

### 2. Synchroniser les fichiers

```bash
cd frontend-client
npm run theme:sync
```

Le script :
- Nettoie `public/theme/` (supprime les anciens HTML et assets)
- Copie les fichiers depuis `theme/source/dist/`
- Génère `public/theme/index.json`

### 3. Vérifier

```bash
# Vérifier que les fichiers sont copiés
ls -la frontend-client/public/theme/*.html

# Vérifier l'index
cat frontend-client/public/theme/index.json
```

## Utilisation

### Preview iframe

Accédez à :

```
http://localhost:3000/theme-preview?file=demo1.html
```

La page affiche :
- **Dropdown** : Sélectionner un fichier HTML
- **Reload** : Recharger l'iframe
- **Open Raw** : Ouvrir le HTML brut dans un nouvel onglet
- **Viewport switcher** : Desktop / Tablet (834px) / Mobile (390px)
- **Back to App** : Retour à l'application principale

### Accès direct

Vous pouvez aussi accéder directement aux fichiers HTML :

```
http://localhost:3000/theme/demo1.html
http://localhost:3000/theme/about.html
...
```

**Important** : Le rendu de `/theme-preview?file=demo1.html` doit être **strictement identique** à `/theme/demo1.html` (pixel-perfect).

## Mise à jour du template

Quand vous modifiez les fichiers source du template :

1. Éditer les fichiers dans `theme/source/dist/`
2. Exécuter `npm run theme:sync`
3. Recharger la page preview

## Commandes

### Synchroniser le template

```bash
cd frontend-client
npm run theme:sync
```

### Démarrer le serveur de développement

```bash
npm run dev
```

### Tests

1. **Vérifier le rendu direct** :
   ```
   http://localhost:3000/theme/demo1.html
   ```

2. **Vérifier le preview iframe** :
   ```
   http://localhost:3000/theme-preview?file=demo1.html
   ```

3. **Comparer** : Les deux doivent être identiques (pixel-perfect)

## Notes techniques

### Isolation

- La route `/theme-preview` utilise un layout isolé (`app/theme-preview/layout.tsx`)
- Le `ThemePreviewWrapper` masque la navbar Vancelian sur `/theme-preview`
- L'iframe garantit l'isolation CSS/JS complète

### Fichiers servis

- Les fichiers dans `public/theme/` sont servis statiquement par Next.js
- Les chemins relatifs dans les HTML (ex: `./assets/...`) fonctionnent car ils sont servis depuis `/theme/`

### Limitations

- Les interactions JavaScript du template fonctionnent normalement dans l'iframe
- Aucun partage d'état entre l'app Next.js et l'iframe (isolation complète)
