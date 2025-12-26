"""
ZAND Bank webhook simulation endpoints (DEV ONLY)
"""

from decimal import Decimal
from uuid import uuid4
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator

from app.infrastructure.database import get_db
from app.infrastructure.settings import get_settings
from app.auth.dependencies import require_user_role, get_user_id_from_principal
from app.auth.oidc import Principal
from app.services.fund_services import record_deposit_blocked
from app.core.transactions.models import Transaction, TransactionType, TransactionStatus
from app.utils.trace_id import get_trace_id

router = APIRouter()

# Don't cache settings at module level - allow patching in tests
def get_settings_instance():
    """Get settings instance (allows patching in tests)"""
    return get_settings()


class SimulateDepositRequest(BaseModel):
    """Request schema for simulating a ZAND deposit"""
    currency: str = Field(default="AED", description="Currency code (must be AED)")
    amount: Decimal = Field(..., gt=0, description="Deposit amount (must be > 0)")
    reference: str | None = Field(None, description="Optional reference (auto-generated if missing)")

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Quantize amount to 2 decimal places"""
        return v.quantize(Decimal('0.01'))

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Ensure currency is AED"""
        if v.upper() != "AED":
            raise ValueError("Currency must be AED")
        return v.upper()


class SimulateDepositResponse(BaseModel):
    """Response schema for simulated deposit"""
    status: str = Field(..., description="Operation status")
    currency: str = Field(..., description="Currency code")
    amount: str = Field(..., description="Deposit amount (as string)")
    reference: str = Field(..., description="Reference identifier")
    operation_id: str = Field(..., description="Operation UUID")
    transaction_id: str | None = Field(None, description="Transaction UUID")
    sim_version: str = Field(default="v1", description="Simulation endpoint version (DEV only)")


def _generate_reference() -> str:
    """Generate a unique reference for simulated deposits"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    short_uuid = str(uuid4())[:8]
    return f"ZAND-SIM-{timestamp}-{short_uuid}"


@router.post(
    "/simulate",
    response_model=SimulateDepositResponse,
    status_code=status.HTTP_200_OK,
    summary="Simulate ZAND deposit webhook (DEV ONLY)",
    description="Simulate an inbound ZAND deposit for the authenticated user. Funds are recorded in WALLET_BLOCKED compartment. DEV ONLY - requires DEV_MODE or local/dev environment.",
)
async def simulate_zand_deposit(
    request: SimulateDepositRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_user_role()),
) -> SimulateDepositResponse:
    """
    Simulate a ZAND Bank deposit webhook for the authenticated user.
    
    This endpoint:
    1. Validates DEV mode/environment
    2. Extracts user_id from JWT principal
    3. Creates Transaction (type=DEPOSIT, status=INITIATED)
    4. Records deposit in WALLET_BLOCKED compartment using record_deposit_blocked()
    5. Returns operation and transaction IDs
    
    DEV ONLY: This endpoint is only available when:
    - ENV is "dev" or "local", OR
    - DEBUG mode is True
    """
    # DEV gate: Check if simulation is allowed
    current_settings = get_settings_instance()  # Get fresh settings (allows patching in tests)
    env_lower = current_settings.ENV.lower()
    is_dev_env = env_lower in ("dev", "local", "development")
    is_debug = current_settings.debug  # debug is a property (not a method)
    
    if not (is_dev_env or is_debug):
        trace_id = get_trace_id(http_request)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "WEBHOOK_SIM_DISABLED",
                    "message": "Webhook simulation disabled. This endpoint is only available in development mode.",
                    "trace_id": trace_id,
                }
            }
        )
    
    # Extract user_id from JWT principal
    user_id = get_user_id_from_principal(principal)
    
    # Generate reference if not provided
    reference = request.reference or _generate_reference()
    
    # Generate idempotency key from reference
    idempotency_key = f"zand-sim-{reference}"
    
    try:
        # Create Transaction record
        transaction = Transaction(
            user_id=user_id,
            type=TransactionType.DEPOSIT,
            status=TransactionStatus.INITIATED,
            transaction_metadata={
                "provider_reference": reference,
                "amount": str(request.amount),
                "currency": request.currency,
                "simulated": True,
                "occurred_at": datetime.utcnow().isoformat(),
            },
        )
        db.add(transaction)
        db.flush()  # Get transaction.id
        
        # Record deposit using existing fund service
        operation = record_deposit_blocked(
            db=db,
            user_id=user_id,
            currency=request.currency,
            amount=request.amount,
            transaction_id=transaction.id,
            idempotency_key=idempotency_key,
            provider_reference=reference,
        )
        
        # Commit transaction
        db.commit()
        
        trace_id = get_trace_id(http_request)
        
        return SimulateDepositResponse(
            status="COMPLETED",
            currency=request.currency,
            amount=str(request.amount),
            reference=reference,
            operation_id=str(operation.id),
            transaction_id=str(transaction.id),
            sim_version="v1",
        )
        
    except HTTPException:
        # Re-raise HTTPException as-is (already has proper error format)
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        trace_id = get_trace_id(http_request)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "DEPOSIT_SIMULATION_FAILED",
                    "message": f"Failed to simulate deposit: {str(e)}",
                    "trace_id": trace_id,
                }
            }
        )

