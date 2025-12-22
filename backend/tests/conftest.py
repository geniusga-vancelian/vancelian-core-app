"""
Pytest configuration and fixtures for end-to-end tests
"""

import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
import redis
from redis import Redis

# Set test environment variables before importing app
os.environ["ENV"] = "test"
# Use 'postgres' service name when running in Docker, 'localhost' when running locally
db_host = os.getenv("TEST_DB_HOST", "postgres")  # Default to 'postgres' for Docker
os.environ["DATABASE_URL"] = f"postgresql://vancelian:vancelian_password@{db_host}:5432/vancelian_core_test"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"  # Use DB 1 for tests
os.environ["SECRET_KEY"] = "test-secret-key-min-32-chars-for-testing-only"
os.environ["LOG_LEVEL"] = "DEBUG"

# OIDC test configuration
os.environ["OIDC_ISSUER_URL"] = "https://test-issuer.example.com"
os.environ["OIDC_AUDIENCE"] = "test-audience"
os.environ["OIDC_JWKS_URL"] = ""  # Will be mocked in tests

from app.infrastructure.database import Base, get_db
from app.main import app
from app.core.users.models import User, UserStatus
from app.core.accounts.models import Account, AccountType
from uuid import uuid4
from decimal import Decimal


# Create test database engine
test_engine = create_engine(
    os.environ["DATABASE_URL"],
    poolclass=StaticPool,
    connect_args={"check_same_thread": False} if "sqlite" in os.environ["DATABASE_URL"] else {},
)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session() -> Session:
    """
    Create a fresh database session for each test.
    Clears all tables before and after each test.
    """
    # Drop and recreate all tables
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def redis_client() -> Redis:
    """
    Get Redis client for tests.
    Clears test database before each test.
    """
    client = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    # Clear test Redis database
    client.flushdb()
    try:
        yield client
    finally:
        # Clean up after test
        client.flushdb()
        client.close()


@pytest.fixture(scope="function")
def client(db_session: Session, redis_client: Redis):
    """
    Create FastAPI test client with dependency overrides.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    # Override database dependency
    app.dependency_overrides[get_db] = override_get_db
    
    # Mock webhook signature verification for tests
    # Set a test secret that will be used for signature verification
    import os
    os.environ["ZAND_WEBHOOK_SECRET"] = "test-webhook-secret-for-testing-only"
    
    # Patch webhook security verification to accept test signatures
    import app.utils.webhook_security as webhook_security_module
    original_verify = webhook_security_module.verify_zand_webhook_security
    
    def mock_verify_webhook_security(payload_body, signature_header, timestamp_header=None):
        # In tests, compute signature with test secret and compare
        import hmac
        import hashlib
        secret = os.environ.get("ZAND_WEBHOOK_SECRET", "")
        if secret and signature_header:
            # Compute expected signature
            expected = hmac.new(
                secret.encode('utf-8'),
                payload_body,
                hashlib.sha256
            ).hexdigest()
            if hmac.compare_digest(expected, signature_header):
                return True, None
        # Accept test-signature-placeholder for convenience in tests
        if signature_header and signature_header.startswith("test-"):
            return True, None
        return False, "Invalid signature for tests"
    
    webhook_security_module.verify_zand_webhook_security = mock_verify_webhook_security
    
    yield TestClient(app)
    
    # Clean up
    app.dependency_overrides.clear()
    webhook_security_module.verify_zand_webhook_security = original_verify


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user"""
    user = User(
        id=uuid4(),
        email="test@example.com",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_internal_account(db_session: Session) -> Account:
    """Create INTERNAL_OMNIBUS account for AED"""
    account = Account(
        id=uuid4(),
        user_id=None,  # System account
        currency="AED",
        account_type=AccountType.INTERNAL_OMNIBUS,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def test_user_with_balance(db_session: Session, test_user: User, test_internal_account: Account) -> User:
    """
    Create a test user with AVAILABLE balance by simulating a completed deposit.
    This creates the necessary wallet accounts and adds funds via ledger entries.
    """
    from app.core.ledger.models import Operation, OperationType, OperationStatus, LedgerEntry, LedgerEntryType
    from app.services.wallet_helpers import ensure_wallet_accounts
    
    # Ensure wallet accounts exist
    wallet_accounts = ensure_wallet_accounts(db_session, test_user.id, "AED")
    available_account_id = wallet_accounts[AccountType.WALLET_AVAILABLE.value]
    
    # Create a deposit operation to add funds
    operation = Operation(
        id=uuid4(),
        type=OperationType.DEPOSIT_AED,
        status=OperationStatus.COMPLETED,
        metadata={"test": "initial_balance"},
    )
    db_session.add(operation)
    db_session.flush()
    
    # Create ledger entries: CREDIT WALLET_AVAILABLE, DEBIT INTERNAL_OMNIBUS
    amount = Decimal("10000.00")
    
    credit_entry = LedgerEntry(
        id=uuid4(),
        operation_id=operation.id,
        account_id=available_account_id,
        amount=amount,
        currency="AED",
        entry_type=LedgerEntryType.CREDIT,
    )
    
    debit_entry = LedgerEntry(
        id=uuid4(),
        operation_id=operation.id,
        account_id=test_internal_account.id,
        amount=-amount,  # Negative for DEBIT
        currency="AED",
        entry_type=LedgerEntryType.DEBIT,
    )
    
    db_session.add(credit_entry)
    db_session.add(debit_entry)
    db_session.commit()
    
    return test_user
