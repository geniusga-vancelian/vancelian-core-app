"""
Offers service v1.1 - Full transactional safety and concurrency control

Business Rules:
1. Offer constraints:
   - max_amount (hard cap)
   - invested_amount (current invested)
   - remaining_amount = max_amount - invested_amount (MUST NEVER go below 0)

2. Concurrency safety (CRITICAL):
   - Use SELECT ... FOR UPDATE on Offer row
   - Investment decision must be atomic

3. Allocation logic:
   - If requested_amount <= remaining_amount: allocate full requested_amount
   - If requested_amount > remaining_amount: allocate ONLY remaining_amount (silent reject excess)
   - If remaining_amount == 0: reject with OFFER_FULL

4. Wallet behavior:
   - On investment request: Create InvestmentIntent with status PENDING (NO ledger movement)
   - On successful allocation: Move allocated amount (AVAILABLE → LOCKED) + create ledger entries
   - On failure: No ledger movement

5. Status lifecycle:
   - InvestmentIntent: PENDING → CONFIRMED | REJECTED
"""

from decimal import Decimal
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from app.core.offers.models import Offer, InvestmentIntent, OfferStatus, InvestmentIntentStatus
from app.core.ledger.models import Operation, OperationType
from app.core.transactions.models import Transaction, TransactionType, TransactionStatus
from app.services.fund_services import lock_funds_for_investment, InsufficientBalanceError, ValidationError
from app.services.transaction_engine import recompute_transaction_status


# Alias for consistency with API layer
class InsufficientAvailableFundsError(InsufficientBalanceError):
    """Raised when user has insufficient available funds for investment"""
    pass


class OfferNotFoundError(Exception):
    """Raised when offer is not found"""
    pass


class OfferNotLiveError(Exception):
    """Raised when offer is not in LIVE status"""
    pass


class OfferCurrencyMismatchError(Exception):
    """Raised when offer currency doesn't match request"""
    pass


class OfferFullError(Exception):
    """Raised when offer has reached max_amount (remaining_amount == 0)"""
    pass


class OfferClosedError(Exception):
    """Raised when offer is CLOSED"""
    pass


def invest_in_offer_v1_1(
    *,
    db: Session,
    user_id: UUID,
    offer_id: UUID,
    amount: Decimal,
    currency: str,
    idempotency_key: str | None = None,
) -> tuple[InvestmentIntent, Decimal]:
    """
    Invest in an offer with full transactional safety (v1.1).
    
    Flow:
    1. Validate amount > 0
    2. Lock offer row with SELECT ... FOR UPDATE (concurrency-safe)
    3. Check idempotency (within same transaction, after lock)
    4. Validate offer.status == LIVE and currency matches
    5. Compute remaining_amount = max_amount - invested_amount
    6. If remaining_amount == 0: create REJECTED intent, raise OfferFullError
    7. Compute allocated_amount = min(requested_amount, remaining_amount)
    8. Create InvestmentIntent with status PENDING
    9. If allocated_amount > 0:
        - Create Transaction record
        - Move funds (AVAILABLE → LOCKED) via ledger
        - Update InvestmentIntent status to CONFIRMED
        - Update offer.invested_amount += allocated_amount
    10. If allocated_amount == 0:
        - Update InvestmentIntent status to REJECTED
        - Do NOT update offer.invested_amount
    11. Return (InvestmentIntent, remaining_after)
    
    Returns:
        Tuple of (InvestmentIntent, remaining_after)
        - InvestmentIntent with allocated_amount and status (PENDING/CONFIRMED/REJECTED)
        - remaining_after: remaining capacity after this investment
    
    Raises:
        ValidationError: Invalid amount (amount <= 0) => 400
        OfferNotFoundError: Offer not found => 404
        OfferNotLiveError: Offer not in LIVE status => 409
        OfferCurrencyMismatchError: Currency mismatch => 409
        OfferFullError: No remaining capacity (remaining_amount == 0) => 409
        OfferClosedError: Offer is CLOSED => 403
        InsufficientBalanceError: User doesn't have enough funds => 409
    
    Note:
        - Caller MUST commit the transaction
        - All writes are atomic within this function
        - remaining_amount MUST NEVER go below 0 (enforced by constraints)
    """
    # Validate amount
    if amount <= 0:
        raise ValidationError("Amount must be greater than 0")
    
    # Lock offer row for update FIRST (concurrency-safe)
    offer = db.execute(
        select(Offer)
        .where(Offer.id == offer_id)
        .with_for_update()
    ).scalar_one_or_none()
    
    if not offer:
        raise OfferNotFoundError(f"Offer {offer_id} not found")
    
    # Check idempotency AFTER lock (within same transaction)
    if idempotency_key:
        existing_intent = db.query(InvestmentIntent).filter(
            InvestmentIntent.idempotency_key == idempotency_key
        ).first()
        if existing_intent:
            # Return existing intent + compute remaining_after
            remaining_after = offer.max_amount - offer.invested_amount
            return existing_intent, max(remaining_after, Decimal('0'))
    
    # Validate offer status
    if offer.status == OfferStatus.CLOSED:
        # Create rejected intent for audit
        intent = InvestmentIntent(
            offer_id=offer_id,
            user_id=user_id,
            requested_amount=amount,
            allocated_amount=Decimal('0'),
            currency=currency,
            status=InvestmentIntentStatus.REJECTED,
            idempotency_key=idempotency_key,
        )
        db.add(intent)
        db.flush()
        raise OfferClosedError(f"Offer is CLOSED")
    
    if offer.status != OfferStatus.LIVE:
        # Create rejected intent for audit
        intent = InvestmentIntent(
            offer_id=offer_id,
            user_id=user_id,
            requested_amount=amount,
            allocated_amount=Decimal('0'),
            currency=currency,
            status=InvestmentIntentStatus.REJECTED,
            idempotency_key=idempotency_key,
        )
        db.add(intent)
        db.flush()
        raise OfferNotLiveError(f"Offer is not LIVE (current status: {offer.status})")
    
    # Validate currency
    if offer.currency != currency:
        intent = InvestmentIntent(
            offer_id=offer_id,
            user_id=user_id,
            requested_amount=amount,
            allocated_amount=Decimal('0'),
            currency=currency,
            status=InvestmentIntentStatus.REJECTED,
            idempotency_key=idempotency_key,
        )
        db.add(intent)
        db.flush()
        raise OfferCurrencyMismatchError(f"Offer currency {offer.currency} does not match request {currency}")
    
    # Compute remaining capacity (while holding lock)
    remaining = offer.max_amount - offer.invested_amount
    
    # Ensure remaining >= 0 (should never be negative due to constraints, but double-check)
    if remaining < 0:
        remaining = Decimal('0')
    
    # Create InvestmentIntent with status PENDING (before allocation)
    intent = InvestmentIntent(
        offer_id=offer_id,
        user_id=user_id,
        requested_amount=amount,
        allocated_amount=Decimal('0'),  # Will be updated after allocation
        currency=currency,
        status=InvestmentIntentStatus.PENDING,
        idempotency_key=idempotency_key,
    )
    db.add(intent)
    db.flush()
    
    # Allocation logic
    if remaining <= 0:
        # Offer is full - reject intent
        intent.status = InvestmentIntentStatus.REJECTED
        intent.allocated_amount = Decimal('0')
        db.flush()
        raise OfferFullError("Offer has reached max_amount (remaining_amount == 0)")
    
    # Compute allocated amount (auto-cap: partial fill if requested > remaining)
    allocated = min(amount, remaining)
    
    # If allocated > 0, move funds and confirm intent
    if allocated > 0:
        # Create Transaction record for user-facing transaction history
        transaction = Transaction(
            user_id=user_id,
            type=TransactionType.INVESTMENT,
            status=TransactionStatus.INITIATED,  # Will be updated to LOCKED after operation
            transaction_metadata={
                "offer_id": str(offer_id),
                "offer_code": offer.code,
                "offer_name": offer.name,
                "currency": currency,
                "requested_amount": str(amount),
                "allocated_amount": str(allocated),
            },
        )
        db.add(transaction)
        db.flush()
        
        # Move funds (AVAILABLE → LOCKED) via ledger
        try:
            operation = lock_funds_for_investment(
                db=db,
                user_id=user_id,
                currency=currency,
                amount=allocated,
                transaction_id=transaction.id,
                reason=f"Investment in offer {offer.code}",
            )
            # Recompute transaction status (should be LOCKED now)
            recompute_transaction_status(db=db, transaction_id=transaction.id)
            
            # Update intent to CONFIRMED
            intent.status = InvestmentIntentStatus.CONFIRMED
            intent.allocated_amount = allocated
            intent.operation_id = operation.id
            db.flush()
            
            # Update offer.invested_amount atomically (while still holding lock)
            # Use SQL UPDATE to prevent lost updates in concurrent scenarios
            db.execute(
                update(Offer)
                .where(Offer.id == offer_id)
                .values(
                    invested_amount=Offer.invested_amount + allocated,
                    committed_amount=Offer.invested_amount + allocated  # Keep in sync
                )
            )
            db.flush()
            
            # Refresh offer object to get updated invested_amount
            db.refresh(offer)
            
        except InsufficientBalanceError as e:
            # Update transaction status to FAILED
            transaction.status = TransactionStatus.FAILED
            db.flush()
            # Reject intent (will be committed by caller even if exception is raised)
            intent.status = InvestmentIntentStatus.REJECTED
            intent.allocated_amount = Decimal('0')
            db.flush()
            # Re-raise as InsufficientAvailableFundsError for API consistency
            raise InsufficientAvailableFundsError("Insufficient available funds for investment") from e
    else:
        # allocated == 0 (should not happen due to remaining > 0 check, but handle gracefully)
        intent.status = InvestmentIntentStatus.REJECTED
        intent.allocated_amount = Decimal('0')
        db.flush()
    
    # Compute remaining_after for response
    remaining_after = offer.max_amount - offer.invested_amount
    remaining_after = max(remaining_after, Decimal('0'))  # Ensure >= 0
    
    # Note: Caller MUST commit the transaction
    # All writes are atomic within this function
    
    return intent, remaining_after

