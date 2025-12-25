# État du Setup Strapi

## Problèmes Identifiés

### 1. Installation des dépendances Strapi
Le build Docker échoue car les versions de packages Strapi ne sont pas compatibles.

**Solution appliquée** : 
- Utilisé Strapi 4.23.3 (stable)
- Plugin i18n 4.7.0 (compatible avec Strapi 4)

**Status** : ✅ Package.json corrigé, build en cours

### 2. NEXT_PUBLIC_STRAPI_URL manquant
La variable `NEXT_PUBLIC_STRAPI_URL` n'est pas présente dans les variables d'environnement du frontend-client.

**Solution** : 
- Variable déjà présente dans docker-compose.dev.yml (ligne 102)
- Nécessite redémarrage du service frontend-client

**Status** : ⏳ À vérifier après redémarrage

### 3. Aucune offre dans FastAPI
Aucune offre n'existe dans la base de données FastAPI, donc impossible de tester le lien avec Strapi.

**Solution** : 
- Créer une offre via l'admin FastAPI (http://localhost:3001/offers/new)
- OU utiliser un endpoint de création d'offre

**Status** : ⏳ À faire manuellement

---

## Prochaines Étapes

### STEP 1: Vérifier que Strapi démarre
```bash
# Attendre que le build termine, puis vérifier
docker compose -f docker-compose.dev.yml logs cms-strapi | tail -50

# Vérifier que le service est up
docker compose -f docker-compose.dev.yml ps cms-strapi

# Tester l'accès
curl http://localhost:1337/admin
```

### STEP 2: Si Strapi démarre correctement
1. Ouvrir http://localhost:1337/admin
2. Créer compte admin (si première fois)
3. Suivre `docs/STRAPI_SETUP_CHECKLIST.md` pour créer les content types

### STEP 3: Créer une offre FastAPI pour tester
1. Se connecter à l'admin FastAPI : http://localhost:3001
2. Aller dans Offers → New
3. Créer une offre minimale
4. Copier l'UUID de l'offre créée

### STEP 4: Créer du contenu Strapi pour cette offre
1. Dans Strapi, créer un OfferMarketing avec l'UUID de l'offre
2. Créer quelques OfferUpdates
3. Publier le contenu

### STEP 5: Tester l'intégration
1. Ouvrir http://localhost:3000/offers/<UUID>
2. Vérifier que le contenu Strapi s'affiche
3. Vérifier la console navigateur (pas d'erreurs)

---

## Commandes de Validation

Une fois Strapi démarré et les content types créés :

```bash
# 1. Obtenir un offer_id
OFFER_ID=$(curl -s http://localhost:8000/api/v1/offers | python3 -c "import sys, json; d=json.load(sys.stdin); print(d[0]['id'] if isinstance(d,list) and len(d) > 0 else '')")

# 2. Tester Global
curl -s "http://localhost:1337/api/global?locale=fr"

# 3. Tester OfferMarketing
curl -s "http://localhost:1337/api/offer-marketings?filters[offer_id][\$eq]=$OFFER_ID&locale=fr&populate=*"

# 4. Tester OfferUpdates
curl -s "http://localhost:1337/api/offer-updates?filters[offer_id][\$eq]=$OFFER_ID&locale=fr&sort=date:desc&populate=*"

# 5. Vérifier frontend
echo "Ouvrir: http://localhost:3000/offers/$OFFER_ID"
```

---

## Notes

- Si le build Strapi continue d'échouer, considérer utiliser `create-strapi-app` localement puis copier la structure
- Les versions Strapi 5.x peuvent ne pas être disponibles encore - Strapi 4.23.3 est la version stable recommandée
- Le plugin i18n doit être compatible avec la version Strapi utilisée


