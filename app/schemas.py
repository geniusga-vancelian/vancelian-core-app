"""
Schémas Pydantic pour Vancelian Core App
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class HealthCheck(BaseModel):
    """Schéma pour le health check"""
    status: str


class MessageResponse(BaseModel):
    """Schéma de réponse générique"""
    message: str
    version: Optional[str] = None
    status: Optional[str] = None

