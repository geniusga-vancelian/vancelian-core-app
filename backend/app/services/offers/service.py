"""
Offers service - Concurrency-safe investment in exclusive offers
"""

from decimal import Decimal
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.offers.models import Offer, OfferInvestment, OfferStatus, OfferInvestmentStatus
from app.core.ledger.models import OperationType
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
) -> OfferInvestment:
    """
    Invest in an offer with concurrency-safe cap enforcement.
    
    Rules:
    1. Lock the offer row with SELECT ... FOR UPDATE
    2. Validate offer.status == LIVE and currency matches
    3. Compute remaining = max_amount - committed_amount
    4. accepted = min(amount, remaining)
    5. Create OfferInvestment with status ACCEPTED/REJECTED
    6. Increase offer.committed_amount += accepted
    7. Move funds ONLY for accepted amount (AVAILABLE -> LOCKED)
    8. Idempotency: if idempotency_key exists, return existing investment
    
    Returns:
        OfferInvestment with accepted_amount and status
    
    Raises:
        OfferNotFoundError: Offer not found
        OfferNotLiveError: Offer not in LIVE status
        OfferCurrencyMismatchError: Currency mismatch
        OfferFullError: No remaining capacity
        InsufficientBalanceError: User doesn't have enough funds
        ValidationError: Invalid amount or other validation error
    """
    # Validate amount
    if amount <= 0:
        raise ValidationError("Amount must be greater than 0")
    
    # Check idempotency first (before locking)
    if idempotency_key:
        existing_investment = db.query(OfferInvestment).filter(
            OfferInvestment.idempotency_key == idempotency_key
        ).first()
        if existing_investment:
            # If investment exists, check if transaction was created
            if existing_investment.operation_id:
                operation = db.query(Operation).filter(Operation.id == existing_investment.operation_id).first()
                if operation and operation.transaction_id:
                    # Transaction already exists, return existing investment
                    return existing_investment
            return existing_investment
    
    # Lock offer row for update (concurrency-safe)
    offer = db.execute(
        select(Offer)
        .where(Offer.id == offer_id)
        .with_for_update()
    ).scalar_one_or_none()
    
    if not offer:
        raise OfferNotFoundError(f"Offer {offer_id} not found")
    
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
    
    # Compute remaining capacity
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
    
    # Compute accepted amount (partial fill on last investor)
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
    
    # Update offer committed amount
    offer.committed_amount += accepted
    db.add(offer)
    db.flush()
    
    # Commit transaction
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValidationError("Investment creation failed due to constraint violation")
    
    return investment

