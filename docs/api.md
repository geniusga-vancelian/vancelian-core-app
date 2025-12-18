# API Documentation

## Authentication

### Local Authentication (DEV mode)

Local authentication is available in development mode and uses email + password with JWT tokens signed with HS256.

**Important**: In DEV mode, JWT `sub` claim is the internal `user.id` (UUID string). In production OIDC mode, `sub` is the external subject from the identity provider.

#### Register

Create a new user account with email and password.

**Endpoint**: `POST /api/v1/auth/register`

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "secure_password_123",
  "first_name": "John",  // Optional
  "last_name": "Doe",    // Optional
  "phone": "+1234567890" // Optional
}
```

**Response** (201 Created):
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com"
}
```

**Error Codes**:
- `409 AUTH_EMAIL_EXISTS`: Email is already registered
- `422 VALIDATION_ERROR`: Password too short (< 8 characters)

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password_123",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

#### Login

Authenticate with email and password, receive JWT token.

**Endpoint**: `POST /api/v1/auth/login`

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "secure_password_123"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 604800,
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "roles": ["USER"]
  }
}
```

**Error Codes**:
- `401 AUTH_INVALID_CREDENTIALS`: Invalid email or password
- `403 USER_SUSPENDED`: User account is suspended

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password_123"
  }'
```

#### Get Current User Profile

Get the authenticated user's profile information.

**Endpoint**: `GET /api/v1/me`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890",
  "roles": ["USER"]
}
```

**Error Codes**:
- `401 AUTH_REQUIRED`: Missing or invalid token
- `404 USER_NOT_FOUND`: User not found

**Example**:
```bash
curl -X GET http://localhost:8000/api/v1/me \
  -H "Authorization: Bearer <access_token>"
```

**Note**: This endpoint works with both local auth tokens (HS256, `sub=user.id`) and OIDC tokens (RS256, `sub=external_subject`).

---

## Admin API

### Resolve User by Email

Resolve a user by email address. Returns user profile information including user_id.

**Endpoint**: `GET /admin/v1/users/resolve?email=<email>`

**Headers**:
```
Authorization: Bearer <admin_token>
```

**Query Parameters**:
- `email` (required): Email address to lookup (case-insensitive)

**Response** (200 OK):
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890",
  "status": "ACTIVE"
}
```

**Error Codes**:
- `400 INVALID_EMAIL`: Invalid email format
- `401 AUTH_REQUIRED`: Missing or invalid token
- `403 FORBIDDEN`: User does not have ADMIN role
- `404 USER_NOT_FOUND`: User not found with provided email
- `422 VALIDATION_ERROR`: Missing email parameter

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/v1/users/resolve?email=user@example.com" \
  -H "Authorization: Bearer <admin_token>"
```

**Note**: Email lookup is case-insensitive. Returns the stored email (typically lowercase) even if uppercase is provided.

---

### Compliance Actions

Actions to finalize deposit review after compliance check. These actions are triggered by ADMIN or COMPLIANCE roles and operate on deposit operations identified by `operation_id`.

#### List Deposits Pending Review

List all deposit operations pending compliance review.

**Endpoint**: `GET /admin/v1/compliance/deposits`

**Headers**:
```
Authorization: Bearer <admin_token>
```

**Query Parameters**:
- `limit` (optional): Maximum number of deposits to return (default: 100, max: 500)
- `offset` (optional): Number of deposits to skip for pagination (default: 0)

**Response** (200 OK):
```json
{
  "deposits": [
    {
      "operation_id": "123e4567-e89b-12d3-a456-426614174001",
      "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
      "created_at": "2025-12-18T10:00:00Z",
      "amount": "1000.00",
      "currency": "AED",
      "status": "COMPLIANCE_REVIEW",
      "user": {
        "user_id": "11111111-1111-1111-1111-111111111111",
        "email": "user@example.com"
      }
    }
  ],
  "total": 1
}
```

**Filtering Rules**:
- Only returns operations where `Operation.type = DEPOSIT_AED`
- Only returns operations where `Operation.status = COMPLETED`
- Only returns transactions where `Transaction.status = COMPLIANCE_REVIEW`
- Results are ordered by `created_at DESC` (newest first)

**Error Codes**:
- `401 UNAUTHORIZED`: Not authenticated
- `403 FORBIDDEN`: User does not have ADMIN or COMPLIANCE role

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/v1/compliance/deposits?limit=50&offset=0" \
  -H "Authorization: Bearer <admin_token>"
```

**Notes**:
- This is a read-only endpoint (no ledger mutations)
- All access is audited via AuditLog with action `COMPLIANCE_LIST_DEPOSITS`
- Pagination-ready: use `limit` and `offset` for large result sets

#### Release Deposit Funds

Release funds from BLOCKED to AVAILABLE after compliance review approval.

**Endpoint**: `POST /admin/v1/compliance/deposits/{operation_id}/release`

**Headers**:
```
Authorization: Bearer <admin_token>
```

**Path Parameters**:
- `operation_id` (required): UUID of the DEPOSIT_AED operation to release

**Request Body**:
```json
{
  "reason": "AML review completed - no suspicious activity detected"
}
```

**Response** (200 OK):
```json
{
  "operation_id": "123e4567-e89b-12d3-a456-426614174001",
  "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "AVAILABLE"
}
```

**Validation Rules**:
- Operation must exist
- Operation.type must be `DEPOSIT_AED`
- Operation.status must be `COMPLETED`
- Associated Transaction.status must be `COMPLIANCE_REVIEW`
- No existing `RELEASE_FUNDS` operation for this transaction (idempotency)

**Error Codes**:
- `404 OPERATION_NOT_FOUND`: Operation not found
- `422 INVALID_OPERATION_TYPE`: Operation type is not DEPOSIT_AED
- `422 INVALID_OPERATION_STATUS`: Operation status is not COMPLETED
- `409 INVALID_TRANSACTION_STATUS`: Transaction status is not COMPLIANCE_REVIEW
- `409 ALREADY_RELEASED`: Funds already released (idempotency)
- `422 INSUFFICIENT_BALANCE`: Insufficient balance in BLOCKED account
- `403 FORBIDDEN`: User does not have ADMIN or COMPLIANCE role

**Example**:
```bash
curl -X POST "http://localhost:8000/admin/v1/compliance/deposits/123e4567-e89b-12d3-a456-426614174001/release" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "AML review completed - no suspicious activity detected"
  }'
```

**What it does**:
1. Validates the deposit operation and transaction status
2. Creates a new `RELEASE_FUNDS` operation
3. Creates ledger entries: DEBIT WALLET_BLOCKED, CREDIT WALLET_AVAILABLE
4. Updates transaction status to `AVAILABLE`
5. Creates AuditLog entry with reason

#### Reject Deposit

Reject a deposit by reversing it (moving funds from BLOCKED back to INTERNAL_OMNIBUS).

**Endpoint**: `POST /admin/v1/compliance/deposits/{operation_id}/reject`

**Headers**:
```
Authorization: Bearer <admin_token>
```

**Path Parameters**:
- `operation_id` (required): UUID of the DEPOSIT_AED operation to reject

**Request Body**:
```json
{
  "reason": "Sanctions match / invalid IBAN"
}
```

**Response** (200 OK):
```json
{
  "operation_id": "123e4567-e89b-12d3-a456-426614174002",
  "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "FAILED"
}
```

**Validation Rules**:
- Operation must exist
- Operation.type must be `DEPOSIT_AED`
- Operation.status must be `COMPLETED`
- Associated Transaction.status must be `COMPLIANCE_REVIEW`
- No existing `REVERSAL_DEPOSIT` operation for this transaction (idempotency)

**Error Codes**:
- `404 OPERATION_NOT_FOUND`: Operation not found
- `422 INVALID_OPERATION_TYPE`: Operation type is not DEPOSIT_AED
- `422 INVALID_OPERATION_STATUS`: Operation status is not COMPLETED
- `409 INVALID_TRANSACTION_STATUS`: Transaction status is not COMPLIANCE_REVIEW
- `409 ALREADY_REJECTED`: Deposit already rejected (idempotency)
- `422 INSUFFICIENT_BALANCE`: Insufficient balance in BLOCKED account
- `403 FORBIDDEN`: User does not have ADMIN or COMPLIANCE role

**Example**:
```bash
curl -X POST "http://localhost:8000/admin/v1/compliance/deposits/123e4567-e89b-12d3-a456-426614174001/reject" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Sanctions match / invalid IBAN"
  }'
```

**What it does**:
1. Validates the deposit operation and transaction status
2. Creates a new `REVERSAL_DEPOSIT` operation
3. Creates ledger entries: DEBIT WALLET_BLOCKED, CREDIT INTERNAL_OMNIBUS
4. Updates transaction status to `FAILED`
5. Creates AuditLog entry with reason

**Notes**:
- Both endpoints preserve ledger immutability (no entries are modified or deleted)
- All actions are fully audited via AuditLog
- Idempotency is enforced (409 Conflict if action already taken)
- Transaction status is automatically recomputed after the operation
