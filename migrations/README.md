# Migrations Alembic

Ce dossier contient les migrations de base de données pour Vancelian Core App.

## Commandes utiles

### Créer une nouvelle migration
```bash
alembic revision --autogenerate -m "Description de la migration"
```

### Appliquer les migrations
```bash
alembic upgrade head
```

### Revenir à une version précédente
```bash
alembic downgrade -1
```

### Voir l'historique des migrations
```bash
alembic history
```

### Voir la version actuelle
```bash
alembic current
```

