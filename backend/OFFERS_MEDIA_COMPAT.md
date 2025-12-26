# Offers Media Backward Compatibility

## Contexte

L'endpoint `/api/v1/offers` retournait une erreur 500 avec le message :
```
ValidationError: MediaItemResponse sort_order Field required + created_at Field required
```

## Problème

Les schémas Pydantic `MediaItemResponse` et `DocumentItemResponse` requéraient les champs `sort_order` et `created_at` comme obligatoires, mais certains media items et documents dans la base de données n'avaient pas ces valeurs (données anciennes ou migration incomplète).

## Solution

### Modifications apportées

1. **Schéma `MediaItemResponse` (`backend/app/schemas/offers.py`)** :
   - `sort_order`: Rendu optionnel avec valeur par défaut `0`
   - `is_cover`: Rendu optionnel avec valeur par défaut `False`
   - `created_at`: Rendu optionnel avec valeur par défaut `None`
   - `kind`: Ajouté comme champ optionnel pour distinguer COVER, PROMO_VIDEO, et gallery items

2. **Schéma `DocumentItemResponse` (`backend/app/schemas/offers.py`)** :
   - `created_at`: Rendu optionnel avec valeur par défaut `None`

2. **Construction des réponses (`backend/app/api/v1/offers.py`)** :
   - Injection de valeurs par défaut lors de la construction de `MediaItemResponse`
   - Injection de `created_at` (optionnel) lors de la construction de `DocumentItemResponse`
   - Tri stable des gallery items : `(sort_order ASC, created_at ASC, id ASC)`
   - Gestion des cas où `created_at` est `None` (mise à `None` dans la réponse)

### Valeurs par défaut

- `sort_order`: `0` (pour permettre un tri stable même sans valeur)
- `is_cover`: `False` (pour éviter de marquer accidentellement un media comme cover)
- `created_at`: `None` (pour indiquer que la date n'est pas disponible)

## Migration future

### Étape 1 : Nettoyage des données existantes

```sql
-- Mettre à jour les media items sans sort_order
UPDATE offer_media SET sort_order = 0 WHERE sort_order IS NULL;

-- Mettre à jour les media items sans created_at (utiliser offer.created_at comme fallback)
UPDATE offer_media om
SET created_at = o.created_at
FROM offers o
WHERE om.offer_id = o.id AND om.created_at IS NULL;

-- Mettre à jour les documents sans created_at (utiliser offer.created_at comme fallback)
UPDATE offer_documents od
SET created_at = o.created_at
FROM offers o
WHERE od.offer_id = o.id AND od.created_at IS NULL;
```

### Étape 2 : Rendre les champs obligatoires dans le schéma

Une fois que toutes les données sont nettoyées, on pourra rendre les champs obligatoires :

```python
# Dans backend/app/schemas/offers.py
sort_order: int = Field(..., description="Sort order")  # Re-devenir obligatoire
created_at: str = Field(..., description="Creation timestamp (ISO format)")  # Re-devenir obligatoire
```

### Étape 3 : Ajouter des contraintes DB

```sql
-- S'assurer que sort_order est toujours présent
ALTER TABLE offer_media ALTER COLUMN sort_order SET NOT NULL;
ALTER TABLE offer_media ALTER COLUMN created_at SET NOT NULL;

-- S'assurer que created_at est toujours présent pour les documents
ALTER TABLE offer_documents ALTER COLUMN created_at SET NOT NULL;
```

## Tests

Les tests dans `backend/tests/test_offers_media_compat.py` vérifient :
- Que l'endpoint retourne 200 même avec des media items sans `sort_order`/`created_at`
- Que les valeurs par défaut sont correctement appliquées
- Que la sérialisation JSON fonctionne avec les valeurs par défaut
- Que les documents sans `created_at` sont également gérés correctement

## Notes

- Le tri stable garantit que l'ordre des media items est prévisible même si plusieurs items ont le même `sort_order`
- L'utilisation de `id` comme dernier critère de tri garantit un ordre déterministe
- Les media items avec `created_at = None` sont triés en dernier (utilisant "9999-12-31T23:59:59" comme valeur de tri)

## Impact

- **Backward compatible** : Les anciennes données continuent de fonctionner
- **Forward compatible** : Les nouvelles données avec tous les champs fonctionnent aussi
- **Pas de breaking change** : Le format JSON reste identique, seuls les champs optionnels peuvent être `None`

