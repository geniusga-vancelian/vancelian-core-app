# API Documentation

> **Note**: All endpoints are READ-ONLY. No mutations, no side effects.

---

## Base URL

- **Development**: `http://localhost:8001`
- **API v1 Prefix**: `/api/v1`

---

## Authentication (OIDC)

All API endpoints require authentication using **OpenID Connect (OIDC)** with **JWT Bearer tokens**.

### Authentication Flow

1. **Obtain JWT Token**: Authenticate with your OIDC provider (e.g., Zitadel) to obtain a JWT access token.
2. **Include in Request**: Send the token in the `Authorization` header as a Bearer token.
3. **Automatic User Provisioning**: On first authentication, a User record is automatically created if it doesn't exist.

### Request Format

```bash
curl -H "Authorization: Bearer <your-jwt-token>" \
     "http://localhost:8001/api/v1/wallet?currency=AED"
```

### JWT Token Requirements

**Required Claims**:
- `sub` (subject): Unique user identifier from OIDC provider
- `iss` (issuer): Must match `OIDC_ISSUER_URL`
- `aud` (audience): Must match `OIDC_AUDIENCE` (client ID)
- `exp` (expiration): Token must not be expired
- `iat` (issued at): Token issuance timestamp
- `nbf` (not before): Token validity start time

**Optional Claims**:
- `email`: User email address (used for user provisioning)
- `preferred_username`: Alternative to email

### Role Mapping (Zitadel-compatible)

Roles are extracted from JWT claims using configurable claim paths. Default paths:
- `realm_access.roles`
- `resource_access.{audience}.roles`
- `roles` (custom claim)

**Supported Roles**:
- `USER`: Required for `/api/v1/*` endpoints
- `ADMIN`, `COMPLIANCE`, `OPS`, `READ_ONLY`: Required for `/admin/v1/*` endpoints

**Role Mapping**:
- External role strings (from JWT) are mapped to internal `Role` enum values
- Case-insensitive matching (e.g., "user" → `USER`)
- If no roles found, defaults to empty list (endpoint-level enforcement applies)

### Authentication Errors

**401 Unauthorized** - Missing or Invalid Token:
```json
{
  "error": {
    "code": "AUTH_REQUIRED",
    "message": "Missing or invalid Authorization header",
    "trace_id": "uuid-v4"
  }
}
```

**401 Unauthorized** - Token Expired:
```json
{
  "error": {
    "code": "AUTH_TOKEN_EXPIRED",
    "message": "Token has expired",
    "trace_id": "uuid-v4"
  }
}
```

**401 Unauthorized** - Invalid Signature:
```json
{
  "error": {
    "code": "AUTH_INVALID_SIGNATURE",
    "message": "Invalid token signature",
    "trace_id": "uuid-v4"
  }
}
```

**403 Forbidden** - Insufficient Permissions:
```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Access denied: required roles [ADMIN, COMPLIANCE, OPS, READ_ONLY]",
    "trace_id": "uuid-v4"
  }
}
```

### Endpoint-Specific Authentication

- **`/api/v1/*`**: Requires `USER` role (or authenticated user, defaults to USER)
- **`/admin/v1/*`**: Requires one of: `ADMIN`, `COMPLIANCE`, `OPS`, `READ_ONLY`
- **`/webhooks/v1/*`**: No OIDC authentication (uses HMAC signature verification only)
- **`/health`, `/ready`**: Public (no authentication required)

### Configuration

Authentication is configured via environment variables:
- `OIDC_ISSUER_URL`: OIDC issuer URL (e.g., `https://auth.zitadel.cloud`)
- `OIDC_AUDIENCE`: Expected audience (client ID)
- `OIDC_JWKS_URL`: Optional explicit JWKS URL (auto-derived if not set)
- `OIDC_ALGORITHMS`: Allowed JWT algorithms (default: `RS256`)
- `OIDC_REQUIRED_SCOPES`: Optional required scopes (comma-separated)
- `OIDC_CLOCK_SKEW_SECONDS`: Clock skew tolerance (default: 60 seconds)
- `OIDC_ROLE_CLAIM_PATHS`: Comma-separated paths to extract roles (default: `realm_access.roles,resource_access.{audience}.roles,roles`)

See `env.example` and `env.prod.example` for full configuration.

---

---

## Endpoints

### GET /api/v1/wallet

Get wallet balances for authenticated user.

**Authentication**: Requires `USER` role (Bearer token in Authorization header)

**Query Parameters**:
- `currency` (optional, default: `"AED"`): ISO 4217 currency code

**Response**:
```json
{
  "currency": "AED",
  "total_balance": "10000.00",
  "available_balance": "7000.00",
  "blocked_balance": "2000.00",
  "locked_balance": "1000.00"
}
```

**Example Request**:
```bash
curl -H "Authorization: Bearer <your-jwt-token>" \
     "http://localhost:8001/api/v1/wallet?currency=AED"
```

**Response Fields**:
- `currency`: ISO 4217 currency code
- `total_balance`: Sum of all wallet compartments (string, decimal-safe)
- `available_balance`: Balance in WALLET_AVAILABLE compartment
- `blocked_balance`: Balance in WALLET_BLOCKED compartment
- `locked_balance`: Balance in WALLET_LOCKED compartment

**Implementation Notes**:
- Uses `get_wallet_balances()` service function
- Balances are computed from LedgerEntry sum (no stored balance)
- READ-ONLY: No mutations, no side effects
- Does NOT expose internal account IDs

---

### GET /api/v1/transactions

Get transaction history for authenticated user.

**Authentication**: Requires `USER` role (Bearer token in Authorization header)

**Query Parameters**:
- `type` (optional): Filter by transaction type (`DEPOSIT`, `WITHDRAWAL`, `INVESTMENT`)
- `status` (optional): Filter by transaction status (`INITIATED`, `COMPLIANCE_REVIEW`, `AVAILABLE`, `FAILED`, `CANCELLED`)
- `limit` (optional, default: `20`, max: `100`): Maximum number of transactions to return

**Response**:
```json
[
  {
    "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
    "type": "DEPOSIT",
    "status": "AVAILABLE",
    "amount": "10000.00",
    "currency": "AED",
    "created_at": "2025-12-18T00:00:00Z"
  }
]
```

**Example Request**:
```bash
# Get all transactions
curl -H "Authorization: Bearer <your-jwt-token>" \
     "http://localhost:8001/api/v1/transactions"

# Filter by type
curl -H "Authorization: Bearer <your-jwt-token>" \
     "http://localhost:8001/api/v1/transactions?type=DEPOSIT"

# Filter by status
curl -H "Authorization: Bearer <your-jwt-token>" \
     "http://localhost:8001/api/v1/transactions?status=AVAILABLE"

# Limit results
curl -H "Authorization: Bearer <your-jwt-token>" \
     "http://localhost:8001/api/v1/transactions?limit=10"
```

**Response Fields**:
- `transaction_id`: Transaction UUID
- `type`: Transaction type (DEPOSIT, WITHDRAWAL, INVESTMENT)
- `status`: Transaction status (derived from Operations)
- `amount`: Transaction amount (sum of ledger entries affecting user wallet, string)
- `currency`: ISO 4217 currency code
- `created_at`: ISO 8601 timestamp (UTC)

**Implementation Notes**:
- Transactions ordered by `created_at DESC`
- Amount = sum of ledger entries for this transaction affecting user wallet accounts
- Does NOT expose internal operations
- Does NOT expose compliance reasons
- Does NOT expose LedgerEntry records
- READ-ONLY: No mutations, no side effects

---

## Data Privacy & Security

### What is NOT Exposed

- ❌ **LedgerEntry records**: Accounting entries are internal-only
- ❌ **Internal account IDs**: User-facing wallet is virtual aggregation
- ❌ **Operations details**: Business logic details are internal
- ❌ **Compliance reasons**: Sensitive audit information
- ❌ **Internal account types**: INTERNAL_OMNIBUS is hidden

### What IS Exposed

- ✅ **Wallet balances**: Aggregated, virtual view
- ✅ **Transaction list**: User-facing saga view
- ✅ **Transaction status**: Derived from Operations

---

## Error Responses

All errors follow the standard error format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {},
    "trace_id": "uuid-v4"
  }
}
```

**Common Error Codes**:
- `400`: Bad Request (invalid query parameters)
- `401`: Unauthorized (authentication required)
- `404`: Not Found
- `500`: Internal Server Error

---

## Rate Limiting & Abuse Protection

> **Status**: Implemented with Redis-backed sliding window algorithm.

All API endpoints are protected by rate limiting to prevent abuse and ensure fair usage.

### Rate Limit Policies

**Endpoint Groups**:
- `/webhooks/v1/*`: **120 requests/minute** (strict)
- `/admin/v1/*`: **60 requests/minute** (strict)
- `/api/v1/*`: **120 requests/minute** (moderate)

**Algorithm**: Sliding window (Redis-backed)

**Configuration**: Environment variables with defaults:
- `RL_WEBHOOK_PER_MIN=120`
- `RL_ADMIN_PER_MIN=60`
- `RL_API_PER_MIN=120`

### Rate Limit Response Headers

All responses include rate limit headers:
- `X-RateLimit-Limit`: Maximum requests allowed per window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when limit resets

### Rate Limit Exceeded Response

When rate limit is exceeded, returns HTTP 429 with standard error format:

```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded. Maximum 120 requests per minute.",
    "details": {
      "endpoint_group": "api",
      "reset_at": 1703001234
    },
    "trace_id": "uuid-v4"
  }
}
```

### Abuse Detection

Repeated rate limit violations on admin endpoints trigger abuse detection:
- Threshold: 5 violations within 10 minutes
- Action: Security event logged with `REPEATED_ABUSE_DETECTED`
- AuditLog entry created for monitoring

**Note**: Health check endpoints (`/health`, `/ready`) and documentation (`/docs`, `/openapi.json`) are excluded from rate limiting.

---

## Versioning

- Current version: `v1`
- Version prefix: `/api/v1`

---

---

## ZAND Webhooks

> **Status**: INTERNAL / BANK ONLY - Not exposed publicly.

### Webhook Security

All ZAND Bank webhooks require **HMAC-SHA256 signature verification** for security.

**Required Headers**:
- `X-Zand-Signature` (MANDATORY): HMAC-SHA256 signature of request body
- `X-Zand-Timestamp` (OPTIONAL): Unix timestamp for replay protection

**Signature Algorithm**:
- Algorithm: `HMAC-SHA256`
- Secret: `ZAND_WEBHOOK_SECRET` (from environment)
- Payload: Raw request body (bytes)
- Format: Hex-encoded signature
- Comparison: Constant-time (prevents timing attacks)

**Replay Protection**:
- If `X-Zand-Timestamp` is provided, timestamp must be within tolerance window
- Default tolerance: 300 seconds (5 minutes)
- Configurable via `ZAND_WEBHOOK_TOLERANCE_SECONDS` environment variable
- If timestamp is outside tolerance, webhook is rejected with 401

**Security Rejection**:
- Missing signature: 401 Unauthorized
- Invalid signature: 401 Unauthorized
- Timestamp outside tolerance: 401 Unauthorized
- All rejections are logged in AuditLog with action `WEBHOOK_REJECTED`

### POST /webhooks/v1/zand/deposit

Receive and process inbound AED deposit notifications from ZAND Bank.

**Security**: Requires HMAC signature verification (see "Webhook Security" above).

**Request Body**:
```json
{
  "provider_event_id": "ZAND-EVT-123456789",
  "iban": "AE123456789012345678901",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "amount": "1000.00",
  "currency": "AED",
  "occurred_at": "2025-12-18T10:00:00Z"
}
```

**Validation**:
- `amount` must be > 0
- `currency` must be "AED"

**Response** (200 OK):
```json
{
  "status": "accepted",
  "transaction_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Security Flow**:
1. Read raw request body
2. Verify HMAC signature (mandatory) - see "Webhook Security" section above
3. Verify timestamp (if provided, optional) - prevents replay attacks
4. Parse and validate payload
5. Check idempotency (Transaction + Operation levels)
6. Process deposit (if new)
7. Commit once

**Idempotence** (Strict):
- `provider_event_id` is MANDATORY and must be unique per deposit event
- Idempotency scope: `provider_event_id` + `transaction_id`
- Duplicate detection at two levels:
  1. Transaction level: Checks `external_reference` (returns existing with 200 OK)
  2. Operation level: Unique constraint on `idempotency_key` (returns 409 Conflict if duplicate operation attempted)
- Duplicate requests return existing Transaction with 200 OK (already processed)
- Duplicate operations (integrity violation) return 409 Conflict
- **Cannot be replayed**: Once processed, duplicate signatures with same `provider_event_id` return existing result

**Behavior**:
1. Verifies HMAC-SHA256 signature (mandatory)
2. Validates timestamp if provided (replay protection)
3. Checks for existing Transaction by `external_reference` (idempotence)
4. Creates Transaction (type=DEPOSIT, status=INITIATED) if new
5. Calls `record_deposit_blocked()` to record deposit in ledger
6. Transaction Status Engine updates status to COMPLIANCE_REVIEW
7. Creates AuditLog entry (action=ZAND_DEPOSIT_RECEIVED)

**Rejection Behavior**:
- Signature missing/invalid: 401 Unauthorized (AuditLog created: WEBHOOK_REJECTED)
- Timestamp outside tolerance: 401 Unauthorized (AuditLog created: WEBHOOK_REJECTED)
- Invalid payload: 422 Unprocessable Entity
- Duplicate operation: 409 Conflict
- All rejections include trace_id for debugging

**Security**:
- HMAC-SHA256 signature verification required (see "Webhook Security" section)
- Replay protection via timestamp validation (configurable tolerance)
- No funds released to AVAILABLE (compliance review required)
- Funds are recorded in WALLET_BLOCKED compartment

**Audit**:
- All webhook receipts logged with trace_id
- AuditLog entry created with OPS role (action=ZAND_DEPOSIT_RECEIVED)
- Rejections logged with AuditLog (action=WEBHOOK_REJECTED)
- Includes provider_event_id and transaction metadata

---

## Compliance APIs

> **Status**: INTERNAL ONLY - Not exposed publicly. Requires COMPLIANCE or OPS role.

### POST /admin/v1/compliance/release-funds

Release funds from BLOCKED to AVAILABLE after compliance review.

Release funds from BLOCKED to AVAILABLE after compliance review.

**Authentication**: Requires `COMPLIANCE` or `OPS` role (Bearer token in Authorization header)

**Access**: COMPLIANCE or OPS role only.

**Request Body**:
```json
{
  "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
  "amount": "10000.00",
  "reason": "AML review completed - no suspicious activity detected"
}
```

**Response** (200 OK):
```json
{
  "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "AVAILABLE"
}
```

**Validations**:
- Transaction must exist
- Transaction.type must be DEPOSIT
- Transaction.status must be COMPLIANCE_REVIEW
- Amount must be > 0
- Amount must be <= blocked balance for transaction/user
- Reason is mandatory (audit trail)

**Business Flow**:
1. Validates transaction state and amount
2. Calls `release_compliance_funds()` service
3. Funds moved: WALLET_BLOCKED → WALLET_AVAILABLE
4. Transaction Status Engine updates status: COMPLIANCE_REVIEW → AVAILABLE
5. Creates AuditLog entry (action=COMPLIANCE_FUNDS_RELEASED)

**Error Responses**:
- `403`: Forbidden (role not allowed)
- `404`: Transaction not found
- `409`: Conflict (transaction in wrong state)
- `422`: Validation error (amount, status, etc.)

**Audit**:
- AuditLog created with:
  - action = "COMPLIANCE_FUNDS_RELEASED"
  - actor_role = COMPLIANCE or OPS
  - entity = Transaction
  - before/after status
  - reason (mandatory)

---

## Investments

### POST /api/v1/investments

Create investment intent and lock funds for investment.

**Authentication**: Requires `USER` role (Bearer token in Authorization header)

**Access**: USER role only.

**Request Body**:
```json
{
  "amount": "5000.00",
  "currency": "AED",
  "offer_id": "123e4567-e89b-12d3-a456-426614174000",
  "reason": "Investment in Exclusive Offer X"
}
```

**Response** (201 Created):
```json
{
  "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "LOCKED"
}
```

**Validations**:
- Amount must be > 0
- Sufficient available_balance required
- Offer must exist (offer_id validation - stub for now)

**Business Flow**:
1. Validates offer exists (stub)
2. Validates sufficient available balance
3. Creates Transaction (type=INVESTMENT, status=INITIATED)
4. Calls `lock_funds_for_investment()` service
5. Funds moved: WALLET_AVAILABLE → WALLET_LOCKED
6. Transaction Status Engine updates status: INITIATED → LOCKED
7. Creates AuditLog entry (action=FUNDS_LOCKED_FOR_INVESTMENT, actor_role=USER)

**Funds Locking**:
- Funds are moved from AVAILABLE to LOCKED compartment
- Locked funds are **non-withdrawable** until investment is completed or cancelled
- Transaction status: LOCKED (funds locked for investment)

**Error Responses**:
- `401`: Unauthorized (authentication required)
- `403`: Forbidden (role not USER)
- `404`: Investment offer not found
- `422`: Validation error (insufficient balance, invalid amount)

**Audit**:
- AuditLog created with:
  - action = "FUNDS_LOCKED_FOR_INVESTMENT"
  - actor_role = USER
  - entity = Transaction
  - metadata includes offer_id, reason

---

**Last Updated**: 2025-12-18

