"""
Investments/Positions API endpoints - READ-ONLY
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.core.offers.models import InvestmentIntent, InvestmentIntentStatus, Offer
from app.core.accounts.models import Account, AccountType
from app.auth.dependencies import require_user_role, get_user_id_from_principal
from app.auth.oidc import Principal
from pydantic import BaseModel, Field

router = APIRouter()


class InvestmentPositionResponse(BaseModel):
    """Investment position response schema"""
    investment_id: str = Field(..., description="InvestmentIntent UUID")
    offer_id: str = Field(..., description="Offer UUID")
    offer_code: str = Field(..., description="Offer code (e.g., NEST-ALBARARI-001)")
    offer_name: str = Field(..., description="Offer name")
    principal: str = Field(..., description="Allocated investment amount (principal)")
    currency: str = Field(..., description="Currency code")
    status: str = Field(..., description="Investment status (ACCEPTED for CONFIRMED, REJECTED, PENDING)")
    created_at: str = Field(..., description="ISO 8601 timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "investment_id": "123e4567-e89b-12d3-a456-426614174000",
                "offer_id": "123e4567-e89b-12d3-a456-426614174001",
                "offer_code": "NEST-ALBARARI-001",
                "offer_name": "Al Barari Exclusive",
                "principal": "10000.00",
                "currency": "AED",
                "status": "ACCEPTED",
                "created_at": "2025-12-18T00:00:00Z",
            }
        }


@router.get(
    "/investments",
    response_model=List[InvestmentPositionResponse],
    summary="Get investment positions",
    description="Get list of user's investment positions (active investments in offers). READ-ONLY endpoint. Requires USER role.",
)
async def get_investments(
    currency: Optional[str] = Query(default=None, description="Filter by currency (e.g., AED)"),
    status: Optional[str] = Query(default=None, description="Filter by investment status (ACCEPTED for CONFIRMED, REJECTED, PENDING)"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of positions to return"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> List[InvestmentPositionResponse]:
    """
    Get investment positions for authenticated user.
    
    Returns InvestmentIntent records (v1.1) ordered by created_at DESC.
    Maps CONFIRMED status to ACCEPTED for frontend compatibility.
    
    READ-ONLY: No side effects, no mutations.
    
    Requires authentication (Bearer token) with USER role.
    """
    user_id = get_user_id_from_principal(principal)
    
    # Build query using InvestmentIntent (v1.1)
    query = db.query(InvestmentIntent).filter(InvestmentIntent.user_id == user_id)
    
    # Apply filters
    if currency:
        query = query.filter(InvestmentIntent.currency == currency)
    
    if status:
        # Map frontend status to backend status
        # Frontend uses "ACCEPTED" but backend uses "CONFIRMED"
        status_mapping = {
            "ACCEPTED": InvestmentIntentStatus.CONFIRMED,
            "REJECTED": InvestmentIntentStatus.REJECTED,
            "PENDING": InvestmentIntentStatus.PENDING,
        }
        if status.upper() in status_mapping:
            backend_status = status_mapping[status.upper()]
            query = query.filter(InvestmentIntent.status == backend_status)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid investment status: {status}. Valid values: ACCEPTED, REJECTED, PENDING")
    
    # Order and limit
    investments = query.order_by(InvestmentIntent.created_at.desc()).limit(limit).all()
    
    # Build response with offer details
    result = []
    for inv in investments:
        # Get offer details
        offer = db.query(Offer).filter(Offer.id == inv.offer_id).first()
        if not offer:
            continue  # Skip if offer not found
        
        # Map backend status to frontend status (CONFIRMED -> ACCEPTED)
        frontend_status = "ACCEPTED" if inv.status == InvestmentIntentStatus.CONFIRMED else inv.status.value
        
        # Normalize datetime
        if inv.created_at.tzinfo is not None:
            created_at_utc = inv.created_at.astimezone(timezone.utc)
            iso_str = created_at_utc.isoformat()
            if iso_str.endswith('+00:00') or iso_str.endswith('-00:00'):
                created_at_str = iso_str[:-6] + 'Z'
            elif '+' in iso_str or (iso_str.count('-') >= 3 and len(iso_str) > 19):
                if len(iso_str) >= 6 and iso_str[-6] in '+-' and iso_str[-3] == ':':
                    created_at_str = iso_str[:-6] + 'Z'
                else:
                    created_at_str = iso_str + 'Z'
            else:
                created_at_str = iso_str + 'Z'
        else:
            created_at_str = inv.created_at.isoformat() + "Z"
        
        result.append(InvestmentPositionResponse(
            investment_id=str(inv.id),
            offer_id=str(inv.offer_id),
            offer_code=offer.code,
            offer_name=offer.name,
            principal=str(inv.allocated_amount),  # Use allocated_amount (v1.1)
            currency=inv.currency,
            status=frontend_status,  # Map CONFIRMED -> ACCEPTED
            created_at=created_at_str,
        ))
    
    return result
