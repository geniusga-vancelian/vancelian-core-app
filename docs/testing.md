# Testing Guide

## Overview

The Vancelian Core App includes comprehensive end-to-end tests that verify the complete lifecycle of funds and transactions, ensuring ledger immutability, compliance workflows, and security controls.

## Test Architecture

### Test Database
- **Database**: PostgreSQL test database (`vancelian_core_test`)
- **Redis**: Test instance (DB 1) or fakeredis for isolation
- **State**: Fresh database state for each test (tables dropped and recreated)
- **Isolation**: Each test runs in a transaction that is rolled back

### Test Infrastructure
- **Framework**: pytest
- **Client**: FastAPI TestClient for API testing
- **Fixtures**: Reusable fixtures for users, accounts, and database sessions
- **Mocking**: External services (ZAND webhook) mocked at boundary; internal services (ledger, fund services) use real implementations

## Test Scenarios

### 1. Happy Path: Deposit → Compliance → Available

**File**: `backend/tests/test_e2e_deposit_flow.py::test_deposit_happy_path_compliance_to_available`

**Scenario**:
1. Create user
2. Simulate ZAND webhook deposit
3. Verify Transaction status = COMPLIANCE_REVIEW
4. Verify funds in WALLET_BLOCKED
5. Call admin compliance release
6. Verify Transaction status = AVAILABLE
7. Verify funds moved BLOCKED → AVAILABLE

**What is Proven**:
- ✅ Webhook integration works correctly
- ✅ Funds are recorded in BLOCKED compartment initially
- ✅ Compliance workflow functions correctly
- ✅ Transaction Status Engine derives status correctly
- ✅ Ledger immutability preserved (no entries modified)
- ✅ Double-entry accounting invariant holds
- ✅ AuditLog entries created with correct actor roles
- ✅ Total balance remains constant (funds moved, not duplicated)

**Ledger Invariants Verified**:
- Sum of credits == Sum of debits for each Operation
- Overall transaction balances correctly
- No LedgerEntry updated or deleted
- TransactionStatus derived from Operation completion

---

### 2. Rejection Path: Deposit → Compliance → Rejected

**File**: `backend/tests/test_e2e_rejection_flow.py::test_deposit_rejection_path`

**Scenario**:
1. Create user
2. Simulate ZAND webhook deposit
3. Verify Transaction status = COMPLIANCE_REVIEW
4. Call admin reject-deposit
5. Verify Transaction status = FAILED
6. Verify funds removed from BLOCKED (returned to OMNIBUS)

**What is Proven**:
- ✅ Rejection workflow functions correctly
- ✅ Funds are properly reversed (reversal entries created)
- ✅ Transaction status updated to FAILED
- ✅ Ledger compensated correctly (reversal offsets original)
- ✅ AuditLog includes mandatory reason
- ✅ Ledger immutability preserved (original entries unchanged, new reversal entries created)

**Ledger Invariants Verified**:
- Original deposit entries remain immutable
- Reversal entries created with correct double-entry
- Overall balance nets to zero after rejection
- No entries deleted or modified

---

### 3. Investment Path: Available → Locked

**File**: `backend/tests/test_e2e_investment_flow.py::test_investment_available_to_locked`

**Scenario**:
1. User has AVAILABLE balance
2. Create investment intent
3. Verify Transaction type = INVESTMENT
4. Verify Transaction status = LOCKED
5. Verify funds moved AVAILABLE → LOCKED
6. Verify user cannot invest more than available

**What is Proven**:
- ✅ Investment flow works correctly
- ✅ Funds locked for investment (non-withdrawable)
- ✅ Balance validation prevents over-investment
- ✅ Transaction Status Engine derives LOCKED status correctly
- ✅ Ledger invariants maintained
- ✅ AuditLog created for investment action

**Ledger Invariants Verified**:
- Double-entry accounting for investment operation
- Total balance unchanged (funds moved between compartments)
- No LedgerEntry modified or deleted

---

### 4. Security Path: Replay & Rate Limit

**File**: `backend/tests/test_e2e_security.py`

**Test: Webhook Replay Protection**
- Sends same webhook event twice
- Verifies HTTP 409 or idempotent 200 (existing transaction returned)
- Ensures no duplicate transactions created

**Test: Rate Limit Enforcement**
- Triggers rate limit by sending multiple requests
- Verifies HTTP 429 with standard error format
- Verifies rate limit headers present

**Test: Security Headers**
- Verifies security headers present in all responses
- Checks X-Content-Type-Options, X-Frame-Options, etc.

**What is Proven**:
- ✅ Idempotency protection works (no duplicate processing)
- ✅ Rate limiting prevents abuse
- ✅ Standard error format for 429 responses
- ✅ Security headers applied consistently

---

## Mandatory Assertions

Every test scenario verifies:

1. **Ledger Invariants**:
   - Sum of credits == Sum of debits per Operation
   - Overall transaction balances correctly
   - No negative balances in final state

2. **Ledger Immutability**:
   - No LedgerEntry updated or deleted
   - All corrections via new Operations (ADJUSTMENT/REVERSAL)
   - Original entries remain unchanged after corrections

3. **Transaction Status Derivation**:
   - Status correctly derived from Operation completion
   - Status transitions follow defined rules
   - No manual status manipulation

4. **Audit Trail**:
   - AuditLog entries created for all critical actions
   - Correct actor_role assigned
   - Mandatory reasons provided for compliance actions

---

## Running Tests Locally

### Prerequisites

1. **Test Database**: PostgreSQL database named `vancelian_core_test`
   ```bash
   createdb vancelian_core_test
   ```

2. **Redis**: Redis instance running (or use fakeredis for tests)

3. **Environment Variables**: Tests use environment variables from `backend/env.example`
   ```bash
   export DATABASE_URL="postgresql://vancelian:vancelian_password@localhost:5432/vancelian_core_test"
   export REDIS_URL="redis://localhost:6379/1"
   ```

### Run All Tests

```bash
cd backend
pytest tests/ -v
```

### Run Specific Test File

```bash
# Deposit flow
pytest tests/test_e2e_deposit_flow.py -v

# Rejection flow
pytest tests/test_e2e_rejection_flow.py -v

# Investment flow
pytest tests/test_e2e_investment_flow.py -v

# Security tests
pytest tests/test_e2e_security.py -v
```

### Run Specific Test

```bash
pytest tests/test_e2e_deposit_flow.py::test_deposit_happy_path_compliance_to_available -v
```

### Run with Coverage

```bash
pytest tests/ --cov=app --cov-report=html
```

### Run in Docker

```bash
# Ensure test database and Redis are accessible
docker-compose -f infra/docker-compose.yml up -d postgres redis

# Run tests
docker-compose -f infra/docker-compose.yml run --rm backend pytest tests/ -v
```

---

## Test Data Management

### Fixtures

**`test_user`**: Creates a basic test user (ACTIVE status)

**`test_user_with_balance`**: Creates a test user with 10,000 AED in AVAILABLE balance (simulated via ledger entries)

**`test_internal_account`**: Creates INTERNAL_OMNIBUS account for AED (system account)

**`db_session`**: Fresh database session with tables recreated for each test

**`redis_client`**: Redis client with test database (cleared before each test)

**`client`**: FastAPI TestClient with dependency overrides

---

## What Each Test Proves

### Ledger Integrity
- ✅ Double-entry accounting enforced
- ✅ Balance calculations correct
- ✅ No data loss or corruption

### Compliance Workflows
- ✅ Deposit → Compliance Review → Available works
- ✅ Deposit → Compliance Review → Rejected works
- ✅ Audit trail complete and accurate

### Security Controls
- ✅ Idempotency prevents duplicate processing
- ✅ Rate limiting prevents abuse
- ✅ Security headers applied

### Business Rules
- ✅ Investment validation (cannot invest more than available)
- ✅ Transaction status derived correctly
- ✅ Fund movements atomic and consistent

---

## Deterministic Tests

All tests are **deterministic** and pass on a clean database:
- ✅ No external dependencies (ZAND mocked)
- ✅ Fresh state for each test
- ✅ No shared state between tests
- ✅ Predictable outcomes

---

## Continuous Integration

Tests should be run in CI/CD pipeline:
- On every commit
- Before deployment
- With test database provisioned
- With Redis test instance

---

**Last Updated**: 2025-12-18

