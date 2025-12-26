# Deposit Simulation Endpoint (DEV ONLY)

This endpoint allows simulating a ZAND Bank deposit for development and testing purposes.

## Endpoint

`POST /api/v1/webhooks/zandbank/simulate`

## Authentication

Requires JWT Bearer token (same as other `/api/v1` endpoints).

## Request Body

```json
{
  "currency": "AED",
  "amount": "1000.00",
  "reference": "ZAND-SIM-20251225120000-abc12345" // Optional, auto-generated if missing
}
```

## Response

```json
{
  "status": "COMPLETED",
  "currency": "AED",
  "amount": "1000.00",
  "reference": "ZAND-SIM-20251225120000-abc12345",
  "operation_id": "123e4567-e89b-12d3-a456-426614174000",
  "transaction_id": "123e4567-e89b-12d3-a456-426614174001"
}
```

## Security

This endpoint is **DEV ONLY**:
- Only available when `ENV` is "dev", "local", or "development"
- OR when `DEBUG` mode is enabled
- Returns `403 Forbidden` in production

## Example Usage

### 1. Login to get token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "your-password"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. Simulate deposit

```bash
TOKEN="YOUR_TOKEN"

curl -i -X POST "http://localhost:8000/api/v1/webhooks/zandbank/simulate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"currency":"AED","amount":"10.00","reference":"ZAND-SIM-TEST"}'
```

Response:
```json
{
  "status": "COMPLETED",
  "currency": "AED",
  "amount": "10.00",
  "reference": "ZAND-SIM-TEST",
  "operation_id": "123e4567-e89b-12d3-a456-426614174000",
  "transaction_id": "123e4567-e89b-12d3-a456-426614174001",
  "sim_version": "v1"
}
```

### 3. Verify wallet balance

```bash
curl -i "http://localhost:8000/api/v1/wallet?currency=AED" \
  -H "Authorization: Bearer $TOKEN"
```

Response:
```json
{
  "currency": "AED",
  "total_balance": "1000.00",
  "available_balance": "0.00",
  "blocked_balance": "1000.00",
  "locked_balance": "0.00"
}
```

**Note**: Deposits go to `blocked_balance` (WALLET_BLOCKED compartment) and require compliance review before becoming available.

## Implementation Details

- Uses existing `record_deposit_blocked()` service function
- Creates a `Transaction` record (type=DEPOSIT, status=INITIATED)
- Creates an `Operation` (type=DEPOSIT_AED, status=COMPLETED)
- Creates `LedgerEntry` records (double-entry: CREDIT WALLET_BLOCKED, DEBIT INTERNAL_OMNIBUS)
- Idempotency: Uses `idempotency_key` based on reference to prevent duplicate processing

