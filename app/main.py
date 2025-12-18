"""
Vancelian Core App - Application principale
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

from .database import engine, Base

# Créer les tables au démarrage (dev seulement)
# En production, utilisez les migrations Alembic
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Vancelian Core API",
    description="""
    API principale (Core) pour la plateforme Vancelian.
    
    ## Fonctionnalités
    
    * **Services métier** : Logique métier principale de la plateforme
    * **Gestion des ressources** : Gestion centralisée des ressources
    
    ## Documentation
    
    Consultez les endpoints ci-dessous pour plus d'informations.
    """,
    version="1.0.0",
)

# Configuration CORS
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",") if origin.strip()]

if not ALLOWED_ORIGINS:
    ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:3001"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.get("/")
async def root():
    """Point d'entrée de l'API"""
    return {
        "message": "Vancelian Core API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Vérification de santé de l'API"""
    return {"status": "healthy"}

