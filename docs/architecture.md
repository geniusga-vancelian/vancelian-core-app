# Architecture

> **Note**: Référez-vous à `VANCELIAN_SYSTEM.md` pour la documentation complète du système.

## Structure du backend (monolithe modulaire)

```
backend/
├── app/
│   ├── main.py                    # Application FastAPI principale
│   ├── core/                      # Domaines métier purs
│   │   ├── ledger/               # Ledger financier immuable
│   │   ├── accounts/             # Comptes/wallets
│   │   ├── investments/          # Investissements
│   │   ├── users/                # Utilisateurs
│   │   ├── kyc/                  # KYC
│   │   ├── compliance/           # Compliance (AuditLog)
│   │   └── common/               # Utilitaires communs (BaseModel)
│   ├── api/                      # Routes FastAPI
│   │   ├── public/               # Endpoints publics (/health, /ready)
│   │   ├── auth/                 # Authentification
│   │   ├── user/                 # Endpoints utilisateur
│   │   ├── admin/                # Endpoints admin (/admin/v1/*)
│   │   ├── webhooks/             # Webhooks (/webhooks/v1/*)
│   │   └── v1/                   # API v1 (/api/v1/*)
│   ├── infrastructure/           # Infrastructure layer
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── redis_client.py      # Redis client
│   │   ├── settings.py          # Pydantic settings
│   │   └── logging_config.py    # Structured logging
│   ├── services/                 # Logique applicative
│   ├── workers/                  # RQ workers et jobs
│   ├── schemas/                  # Schémas Pydantic
│   ├── security/                 # RBAC et auth
│   └── utils/                    # Utilitaires (trace_id, idempotency)
├── alembic/                      # Migrations Alembic
├── tests/                        # Tests pytest
└── requirements.txt              # Dépendances Python
```

## Principes architecturaux

### 1. PostgreSQL est la source de vérité
- Toutes les données critiques sont stockées dans PostgreSQL
- Redis est utilisé uniquement pour le cache et les queues

### 2. Ledger financier immuable
Les entrées `LedgerEntry` sont **write-once** :
- ❌ Pas d'UPDATE
- ❌ Pas de DELETE
- ✅ Toute correction se fait via une nouvelle Operation de type `ADJUSTMENT` ou `REVERSAL`

**Application-level protection:**
- Les modèles SQLAlchemy n'exposent pas de méthodes update/delete pour LedgerEntry
- Les services métier doivent utiliser des Operations pour toute modification

**Database-level strategy (documented, not yet implemented):**
- Envisager des triggers PostgreSQL pour bloquer UPDATE/DELETE sur `ledger_entries`
- Alternative: utiliser des vues read-only et des fonctions stockées pour les écritures

### 3. Double-entry comptable
Toute Operation qui touche le ledger doit créer des LedgerEntry respectant :
- La somme des CREDIT = la somme des DEBIT (à la devise près)
- Invariant: Pour une Operation donnée, `total_credits == total_debits`

### 4. Idempotence
Tout endpoint "qui crée" doit accepter une `idempotency_key` :
- Stockée sur l'Operation
- Si la même `idempotency_key` revient : retourner le résultat existant

### 5. Séparation des couches
- **Core**: Domaines métier purs (modèles, règles métier)
- **Services**: Logique applicative orchestrant les domaines
- **API**: Routers FastAPI (validation, sérialisation)
- **Infrastructure**: DB, Redis, logging, settings

## Data Model

> **Reference**: See `VANCELIAN_SYSTEM.md` Section 4 for complete ledger and financial model definitions.

### Transaction vs Operation vs LedgerEntry

**Transaction** (Saga layer - User-facing):
- Represents a user-visible flow composed of multiple Operations
- Status can evolve: INITIATED → COMPLIANCE_REVIEW → AVAILABLE → etc.
- Example: A DEPOSIT transaction includes Operations for KYC validation and ledger credit
- Mutable: status changes as the saga progresses

**Operation** (Immutable - Audit-proof):
- Represents the business meaning of an action
- Groups multiple LedgerEntry (double-entry accounting)
- Status immutable after COMPLETED - corrections use new Operations (ADJUSTMENT/REVERSAL)
- Always audited
- May be part of a Transaction saga

**LedgerEntry** (Immutable - Accounting-only):
- Represents a single financial movement (CREDIT or DEBIT)
- Write-once: never updated or deleted
- Balance = SUM(ledger_entries.amount) per account
- Corrections via new Operations only

**Transaction status** is derived from the status of its Operations. A Transaction is AVAILABLE when all required Operations are COMPLETED.

### User
Represents a user in the Vancelian platform.
- `id` (UUID, primary key)
- `email` (string, unique, indexed)
- `status` (enum: ACTIVE, SUSPENDED)
- `created_at`, `updated_at` (timezone-aware timestamps)

### Account
Represents a virtual compartment for funds in a specific currency. A "wallet" is a virtual concept - a user can have multiple accounts per currency (one per account_type). Balance is calculated from LedgerEntry sum, not stored.
- `id` (UUID, primary key)
- `user_id` (FK to User, indexed)
- `currency` (ISO 4217, e.g., AED, indexed)
- `account_type` (enum: WALLET_AVAILABLE, WALLET_BLOCKED, WALLET_LOCKED, INTERNAL_OMNIBUS, and legacy WALLET, INTERNAL_BLOCKED)
- `created_at`, `updated_at` (timezone-aware timestamps)
- **UNIQUE constraint**: (user_id, currency, account_type) - one account per combination

### Transaction
Represents a user-visible saga/flow composed of multiple Operations. Transaction status evolves based on Operation statuses. Example: A DEPOSIT transaction may include KYC validation and deposit Operations.
- `id` (UUID, primary key)
- `user_id` (FK to User, indexed)
- `type` (enum: DEPOSIT, WITHDRAWAL, INVESTMENT, indexed)
- `status` (enum: INITIATED, COMPLIANCE_REVIEW, AVAILABLE, FAILED, CANCELLED, indexed)
- `external_reference` (string, nullable, indexed, e.g., ZAND Bank reference)
- `metadata` (JSONB, nullable)
- `created_at`, `updated_at` (timezone-aware timestamps)

### Operation
Represents the business meaning of an action. Groups multiple LedgerEntry and is always audited. May be part of a Transaction saga. Immutable after COMPLETED.
- `id` (UUID, primary key)
- `transaction_id` (FK to Transaction, nullable, indexed)
- `type` (enum: DEPOSIT_AED, INVEST_EXCLUSIVE, ADJUSTMENT, REVERSAL, indexed)
- `status` (enum: PENDING, COMPLETED, FAILED, CANCELLED, indexed)
- `idempotency_key` (string, unique, nullable, indexed)
- `metadata` (JSONB, nullable)
- `created_at`, `updated_at` (timezone-aware timestamps)

### LedgerEntry (IMMUTABLE)
Each financial movement creates a ledger line. **LedgerEntry is immutable (write-once)** - never updated or deleted. Corrections must be done via a new Operation (ADJUSTMENT or REVERSAL). The balance of an Account = SUM(ledger_entries.amount) WHERE account_id = account.id.
- `id` (UUID, primary key)
- `operation_id` (FK to Operation, indexed)
- `account_id` (FK to Account, indexed)
- `amount` (NUMERIC(24, 8), positive or negative)
- `currency` (ISO 4217, e.g., AED)
- `entry_type` (enum: CREDIT, DEBIT, indexed)
- `created_at` (timezone-aware timestamp)
- ❌ **No `updated_at`** - entries are immutable

### AuditLog
Audit trail for all critical actions. Tracks who did what, when, and why.
- `id` (UUID, primary key)
- `actor_user_id` (FK to User, nullable, indexed)
- `actor_role` (enum: USER, ADMIN, COMPLIANCE, OPS, READ_ONLY, indexed)
- `action` (string, indexed)
- `entity_type` (string, indexed)
- `entity_id` (UUID, nullable, indexed)
- `before`, `after` (JSONB, nullable)
- `reason` (text, nullable, required for sensitive actions)
- `ip` (string, nullable, IPv6 max length)
- `created_at` (timezone-aware timestamp)

## RBAC (Role-Based Access Control)

Rôles disponibles:
- `USER`: Utilisateur standard
- `ADMIN`: Administrateur
- `COMPLIANCE`: Équipe compliance
- `OPS`: Opérations
- `READ_ONLY`: Lecture seule

**Status**: Stub implémenté - OIDC/JWT à intégrer (voir `docs/security.md`)

## Wallet Virtualization via Account Types

A user's "wallet" is a **virtual aggregation** of multiple Account records. Each Account represents a compartment with different fund availability rules.

### Account Compartments

- **WALLET_AVAILABLE**: Funds available for user operations (withdrawals, investments). Default compartment for new deposits.
- **WALLET_BLOCKED**: Funds blocked, typically during compliance review. Funds cannot be used until moved to AVAILABLE.
- **WALLET_LOCKED**: Funds locked by the system (e.g., fraud detection, security holds). Requires administrative action to unlock.
- **INTERNAL_OMNIBUS**: Internal platform account for operational purposes (not user-facing).

### Fund Movement

Funds move between account compartments via **LedgerEntry** records (double-entry):
- Moving funds from AVAILABLE to BLOCKED creates:
  - DEBIT entry on WALLET_AVAILABLE account
  - CREDIT entry on WALLET_BLOCKED account
- This is orchestrated through **Operation** and tracked in **Transaction** sagas

### Constraints

- One account per (user_id, currency, account_type) combination
- No balance field is authoritative - balance = SUM(ledger_entries.amount) per account
- Wallet balance (virtual) = SUM(all account balances) per currency

**Reference**: See `VANCELIAN_SYSTEM.md` Section 4.1 for detailed wallet architecture.

## Fund Movements via Operations

Fund movements between wallet compartments are orchestrated through **Operations** that create **LedgerEntry** records (double-entry accounting). All operations are atomic and audit-proof.

### Service Layer Functions

**Account Provisioning**:
- `ensure_wallet_accounts(user_id, currency)`: Ensures WALLET_AVAILABLE, WALLET_BLOCKED, WALLET_LOCKED accounts exist

**Balance Queries** (read-only):
- `get_account_balance(account_id)`: Returns balance = SUM(ledger_entries.amount)
- `get_wallet_balances(user_id, currency)`: Returns balances for all compartments

**Fund Movement Services**:

1. **`record_deposit_blocked`**: Record deposit into WALLET_BLOCKED
   - Operation: DEPOSIT_AED, COMPLETED
   - LedgerEntries: CREDIT WALLET_BLOCKED, DEBIT INTERNAL_OMNIBUS
   - Idempotency support via idempotency_key

2. **`release_compliance_funds`**: Move funds from BLOCKED → AVAILABLE
   - Operation: RELEASE_FUNDS, COMPLETED
   - LedgerEntries: DEBIT WALLET_BLOCKED, CREDIT WALLET_AVAILABLE
   - Validates sufficient balance
   - Requires reason (audit trail)

3. **`lock_funds_for_investment`**: Move funds from AVAILABLE → LOCKED
   - Operation: INVEST_EXCLUSIVE, COMPLETED
   - LedgerEntries: DEBIT WALLET_AVAILABLE, CREDIT WALLET_LOCKED
   - Validates sufficient balance

### Example Flows

**Deposit Flow**:
```
1. Deposit received from external provider
2. record_deposit_blocked() creates:
   - Operation (DEPOSIT_AED, COMPLETED)
   - LedgerEntry: +amount to WALLET_BLOCKED (CREDIT)
   - LedgerEntry: -amount from INTERNAL_OMNIBUS (DEBIT)
   - AuditLog: DEPOSIT_RECORDED
3. Funds are in BLOCKED compartment (pending compliance)
```

**Compliance Release Flow**:
```
1. Compliance review passes
2. release_compliance_funds() creates:
   - Operation (RELEASE_FUNDS, COMPLETED)
   - LedgerEntry: -amount from WALLET_BLOCKED (DEBIT)
   - LedgerEntry: +amount to WALLET_AVAILABLE (CREDIT)
   - AuditLog: COMPLIANCE_RELEASE (with reason)
3. Funds become available for user operations
```

**Investment Lock Flow**:
```
1. User initiates investment
2. lock_funds_for_investment() creates:
   - Operation (INVEST_EXCLUSIVE, COMPLETED)
   - LedgerEntry: -amount from WALLET_AVAILABLE (DEBIT)
   - LedgerEntry: +amount to WALLET_LOCKED (CREDIT)
   - AuditLog: FUNDS_LOCKED_FOR_INVESTMENT
3. Funds are locked for investment processing
```

### Atomicity & Integrity

- All operations run inside database transactions
- Double-entry invariant enforced: Sum of CREDITS = Sum of DEBITS per Operation
- Validation errors fail fast (before creating Operation)
- InsufficientBalanceError raised if balance check fails
- All operations create AuditLog entries

**Note**: These are internal service functions - no API endpoints. Orchestrated through Transaction sagas.

## Transaction Status Engine

The Transaction Status Engine automatically updates `Transaction.status` based on completed Operations. Transaction status is **derived**, not manually set.

### Why Derived Status?

- **Audit-proof**: Status reflects actual Operation completion
- **Consistency**: Cannot have inconsistent state (e.g., AVAILABLE without RELEASE_FUNDS)
- **Traceability**: Status changes are implicit in Operation completion

### Status Rules (Deterministic Mapping)

**TransactionType = DEPOSIT**:

1. **INITIATED** → No completed Operation yet
2. **COMPLIANCE_REVIEW** → Operation `DEPOSIT_AED` completed, but no `RELEASE_FUNDS` yet
3. **AVAILABLE** → Operation `RELEASE_FUNDS` completed
4. **FAILED** → Any Operation FAILED
5. **CANCELLED** → Explicit cancellation (future)

**TransactionType = INVESTMENT**:

1. **INITIATED** → No completed Operation yet
2. **COMPLIANCE_REVIEW** → Operation `INVEST_EXCLUSIVE` completed (funds locked)
3. **AVAILABLE** → Investment finalized (future)
4. **FAILED** → Any Operation FAILED
5. **CANCELLED** → Explicit cancellation (future)

### Service Function

**`recompute_transaction_status(db, transaction_id)`**:
- Loads Transaction and all linked Operations
- Computes correct status via rules
- Updates `Transaction.status` ONLY if changed
- Idempotent: Safe to call multiple times
- Side-effect free: Only updates Transaction.status

### Integration

Status recomputation is automatically triggered at the end of:
- `record_deposit_blocked()` - Updates DEPOSIT transactions
- `release_compliance_funds()` - Updates DEPOSIT transactions (COMPLIANCE_REVIEW → AVAILABLE)
- `lock_funds_for_investment()` - Updates INVESTMENT transactions

### Example: Deposit Timeline

```
1. Transaction created: status = INITIATED
2. record_deposit_blocked() completes:
   - Creates Operation (DEPOSIT_AED, COMPLETED)
   - Triggers recompute_transaction_status()
   - Transaction status → COMPLIANCE_REVIEW
3. release_compliance_funds() completes:
   - Creates Operation (RELEASE_FUNDS, COMPLETED)
   - Triggers recompute_transaction_status()
   - Transaction status → AVAILABLE
```

**Result**: Transaction status accurately reflects fund availability without manual updates.

## Security Middlewares

The application includes several security middlewares that execute on every request:

### 1. Trace ID Middleware
- Generates unique trace ID for each request
- Adds trace ID to logging context
- Included in all error responses

**Execution Order**: Outermost (first to execute)

### 2. Rate Limiting Middleware
- Redis-backed sliding window rate limiter
- Configurable limits per endpoint group:
  - Webhooks: 120 req/min (strict)
  - Admin: 60 req/min (strict)
  - API: 120 req/min (moderate)
- Adds rate limit headers to all responses
- Returns HTTP 429 with standard error format when exceeded
- Logs security events for rate limit violations

**Execution Order**: Middle

### 3. Security Headers Middleware
- Adds security headers to all responses:
  - `X-Content-Type-Options: nosniff` - Prevents MIME sniffing
  - `X-Frame-Options: DENY` - Prevents clickjacking
  - `Referrer-Policy: no-referrer` - No referrer info leaked
  - `Permissions-Policy: camera=(), microphone=(), geolocation=()` - Restricts browser features
  - `Strict-Transport-Security` - HSTS (only if `ENABLE_HSTS=true`)
- HSTS disabled by default for local development

**Execution Order**: Innermost (last to execute)

### Security Event Logging

Security events are logged and audited:
- Rate limit exceeded events
- Webhook signature failures
- Unauthorized access attempts
- Repeated abuse patterns

**Abuse Detection**:
- Tracks repeated violations (Redis-backed counter)
- Threshold: 5 violations within 10 minutes (configurable)
- Creates AuditLog entries for monitoring

**Log Sanitization**:
- Secrets are redacted from logs (signatures, tokens, etc.)
- AuditLog entries include sanitized details
