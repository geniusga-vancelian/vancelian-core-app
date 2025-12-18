"""
Common Pydantic schemas
"""

from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class HealthResponse(BaseModel):
    """Health check response"""
    status: str


class ReadyResponse(BaseModel):
    """Readiness check response"""
    status: str
    database: str
    redis: str

