"""
Offers service - Concurrency-safe investment in exclusive offers
"""

from decimal import Decimal
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.offers.models import Offer, OfferInvestment, OfferStatus, OfferInvestmentStatus
from app.core.ledger.models import Operation, OperationType
from app.core.transactions.models import Transaction, TransactionType, TransactionStatus
from app.services.fund_services import lock_funds_for_investment, InsufficientBalanceError, ValidationError
from app.services.transaction_engine import recompute_transaction_status


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
    """Raised when offer has reached max_amount"""
    pass


def invest_in_offer(
    *,
    db: Session,
    user_id: UUID,
    offer_id: UUID,
    amount: Decimal,
    currency: str,
    idempotency_key: str | None = None,
) -> tuple[OfferInvestment, Decimal]:
    """
    Invest in an offer with concurrency-safe cap enforcement.
    
    Rules:
    1. Lock the offer row with SELECT ... FOR UPDATE (DB-level row lock)
    2. Check idempotency AFTER lock (within same transaction)
    3. Validate offer.status == LIVE and currency matches
    4. Compute remaining = max_amount - committed_amount
    5. If remaining <= 0 => raise OfferFullError (409)
    6. accepted = min(amount, remaining) (auto-cap)
    7. Create OfferInvestment with status ACCEPTED/REJECTED
    8. Increase offer.committed_amount += accepted
    9. Move funds ONLY for accepted amount (AVAILABLE -> LOCKED)
    10. All writes in ONE DB transaction (caller must commit)
    
    Returns:
        Tuple of (OfferInvestment, remaining_after)
        - OfferInvestment with accepted_amount and status
        - remaining_after: remaining capacity after this investment
    
    Raises:
        ValidationError: Invalid amount (amount <= 0) => 400
        OfferNotFoundError: Offer not found => 404
        OfferNotLiveError: Offer not in LIVE status => 409
        OfferCurrencyMismatchError: Currency mismatch => 409
        OfferFullError: No remaining capacity (remaining <= 0) => 409
        InsufficientBalanceError: User doesn't have enough funds => 409
    
    Note:
        - Caller MUST commit the transaction
        - All writes are atomic within this function
        - Idempotency is checked AFTER lock to prevent race conditions
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
    # This prevents race conditions where two requests with same key arrive simultaneously
    if idempotency_key:
        existing_investment = db.query(OfferInvestment).filter(
            OfferInvestment.idempotency_key == idempotency_key
        ).first()
        if existing_investment:
            # Return existing investment + compute remaining_after
            remaining_after = offer.max_amount - offer.committed_amount
            return existing_investment, remaining_after
    
    # Validate offer status
    if offer.status != OfferStatus.LIVE:
        # Create rejected investment record for audit
        investment = OfferInvestment(
            offer_id=offer_id,
            user_id=user_id,
            requested_amount=amount,
            accepted_amount=Decimal('0'),
            currency=currency,
            status=OfferInvestmentStatus.REJECTED,
            idempotency_key=idempotency_key,
        )
        db.add(investment)
        db.flush()
        raise OfferNotLiveError(f"Offer is not LIVE (current status: {offer.status})")
    
    # Validate currency
    if offer.currency != currency:
        investment = OfferInvestment(
            offer_id=offer_id,
            user_id=user_id,
            requested_amount=amount,
            accepted_amount=Decimal('0'),
            currency=currency,
            status=OfferInvestmentStatus.REJECTED,
            idempotency_key=idempotency_key,
        )
        db.add(investment)
        db.flush()
        raise OfferCurrencyMismatchError(f"Offer currency {offer.currency} does not match request {currency}")
    
    # Compute remaining capacity (while holding lock)
    remaining = offer.max_amount - offer.committed_amount
    
    if remaining <= 0:
        # Offer is full - create rejected investment
        investment = OfferInvestment(
            offer_id=offer_id,
            user_id=user_id,
            requested_amount=amount,
            accepted_amount=Decimal('0'),
            currency=currency,
            status=OfferInvestmentStatus.REJECTED,
            idempotency_key=idempotency_key,
        )
        db.add(investment)
        db.flush()
        raise OfferFullError("Offer has reached max_amount")
    
    # Compute accepted amount (auto-cap: partial fill on last investor)
    accepted = min(amount, remaining)
    
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
            "accepted_amount": str(accepted),
        },
    )
    db.add(transaction)
    db.flush()
    
    # Create operation and move funds ONLY for accepted amount
    operation = None
    if accepted > 0:
        try:
            operation = lock_funds_for_investment(
                db=db,
                user_id=user_id,
                currency=currency,
                amount=accepted,
                transaction_id=transaction.id,  # Link operation to transaction
                reason=f"Investment in offer {offer.code}",
            )
            # Recompute transaction status (should be LOCKED now)
            recompute_transaction_status(db=db, transaction_id=transaction.id)
        except InsufficientBalanceError as e:
            # Update transaction status to FAILED
            transaction.status = TransactionStatus.FAILED
            db.flush()
            # Create rejected investment for audit
            investment = OfferInvestment(
                offer_id=offer_id,
                user_id=user_id,
                requested_amount=amount,
                accepted_amount=Decimal('0'),
                currency=currency,
                status=OfferInvestmentStatus.REJECTED,
                idempotency_key=idempotency_key,
            )
            db.add(investment)
            db.flush()
            raise
    
    # Create investment record
    investment = OfferInvestment(
        offer_id=offer_id,
        user_id=user_id,
        requested_amount=amount,
        accepted_amount=accepted,
        currency=currency,
        status=OfferInvestmentStatus.ACCEPTED if accepted > 0 else OfferInvestmentStatus.REJECTED,
        idempotency_key=idempotency_key,
        operation_id=operation.id if operation else None,
    )
    db.add(investment)
    db.flush()
    
    # Update offer committed amount (while still holding lock)
    offer.committed_amount += accepted
    db.add(offer)
    db.flush()
    
    # Compute remaining_after for response
    remaining_after = offer.max_amount - offer.committed_amount
    
    # Note: Caller MUST commit the transaction
    # All writes are atomic within this function
    
    return investment, remaining_after

