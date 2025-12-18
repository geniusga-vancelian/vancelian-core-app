# Vancelian Core App

Application principale (Core) pour la plateforme Vancelian.

## Architecture

- **Backend** : FastAPI (Python) avec PostgreSQL
- **Services** : Services métier principaux de la plateforme

## Structure du projet

```
vancelian-core-app/
├── app/
│   ├── main.py          # Application principale et endpoints
│   ├── models.py        # Modèles SQLAlchemy
│   ├── database.py      # Configuration base de données
│   ├── schemas.py       # Schémas Pydantic
│   ├── api/             # Routes API
│   │   └── routers/     # Routers par domaine
│   └── services/        # Services métier
├── migrations/          # Migrations Alembic
├── requirements.txt     # Dépendances Python
└── .env.example        # Exemple de variables d'environnement
```

## Installation

1. Créer un environnement virtuel :
```bash
python3 -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

2. Installer les dépendances :
```bash
pip install -r requirements.txt
```

3. Configurer les variables d'environnement :
```bash
cp .env.example .env
# Éditer .env avec vos configurations
```

4. Appliquer les migrations :
```bash
alembic upgrade head
```

## Démarrage

```bash
uvicorn app.main:app --reload --port 8001
```

L'API sera accessible sur `http://localhost:8001`

## Documentation API

Une fois l'application démarrée, la documentation interactive est disponible sur :
- Swagger UI : `http://localhost:8001/docs`
- ReDoc : `http://localhost:8001/redoc`

