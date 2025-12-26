# Correction Installation Strapi

## Problème

Le build Docker de Strapi échoue car les versions exactes des packages ne sont pas disponibles sur npm.

## Solution Recommandée

**Option 1 : Utiliser create-strapi-app (Recommandé)**

Créer un projet Strapi propre localement, puis copier la configuration :

```bash
# Sur votre machine locale (hors Docker)
npx create-strapi-app@latest strapi-temp --quickstart --no-run

# Copier le package.json généré vers cms-strapi/package.json
# Copier la structure config/ générée
# Adapter les fichiers config pour utiliser les variables d'env Docker
```

**Option 2 : Simplifier package.json**

Utiliser uniquement les dépendances essentielles et laisser npm résoudre :

```json
{
  "dependencies": {
    "@strapi/strapi": "^4.23.3",
    "pg": "^8.13.1"
  }
}
```

Puis installer les plugins via l'interface Strapi Admin après le premier démarrage.

**Option 3 : Utiliser une version LTS connue**

Strapi 4.22.0 est une version stable testée :

```json
{
  "dependencies": {
    "@strapi/strapi": "4.22.0",
    "@strapi/plugin-users-permissions": "4.22.0",
    "@strapi/plugin-i18n": "4.7.0",
    "@strapi/plugin-upload": "4.22.0",
    "@strapi/provider-upload-aws-s3": "4.22.0",
    "pg": "^8.13.1"
  }
}
```

## Action Immédiate

Pour débloquer rapidement, utiliser **Option 1** : créer le projet Strapi localement avec create-strapi-app, puis adapter la config pour Docker.

---

## Alternative : Setup Manuel Post-Installation

Si le build continue d'échouer, on peut :

1. Créer Strapi localement avec `create-strapi-app`
2. Copier toute la structure vers `cms-strapi/`
3. Adapter `config/database.js` pour utiliser les variables d'env Docker
4. Adapter `config/server.js` pour utiliser les variables d'env Docker
5. Rebuild Docker

C'est plus sûr car `create-strapi-app` génère un package.json qui fonctionne.



