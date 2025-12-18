# CI/CD Pipeline Documentation

## Overview

The Vancelian Core App uses GitHub Actions for continuous integration (CI). The pipeline ensures code quality, runs automated tests, verifies database migrations, and performs security baseline checks.

## Pipeline Workflow

**File**: `.github/workflows/ci.yml`

**Trigger Events**:
- Pull requests to `main` or `develop` branches
- Pushes to `main` or `develop` branches

## Pipeline Steps

### 1. Setup

- **Checkout code**: Checks out the repository code
- **Set up Python 3.12**: Configures Python environment with caching
- **Install dependencies**: Installs Python packages from `requirements.txt`

### 2. Services

The pipeline starts required services:

- **PostgreSQL 15**: Test database (`vancelian_core_test`)
  - User: `vancelian`
  - Password: `vancelian_password`
  - Port: 5432
  - Health checks configured

- **Redis 7**: Test Redis instance
  - Port: 6379
  - Health checks configured

### 3. Environment Configuration

Test environment variables are set:
- `ENV=test`
- `DATABASE_URL`: PostgreSQL test database
- `REDIS_URL`: Redis test instance (DB 1)
- `SECRET_KEY`: Test secret key
- `ZAND_WEBHOOK_SECRET`: Test webhook secret
- Rate limiting configuration
- Security headers configuration

### 4. Migration Safety Check

**Purpose**: Verify that migrations can be applied to an empty database.

**Steps**:
1. Apply migrations to test database: `alembic upgrade head`
2. Create fresh database: `vancelian_core_migration_test`
3. Apply migrations to fresh database (verifies empty DB migration)
4. Check current migration state: `alembic current`

**Failure**: Pipeline fails if migrations cannot be applied to an empty database.

### 5. Security Baseline Checks

**Script**: `backend/scripts/security_check.py`

**Checks**:
- ✅ Required environment variables exist (`DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`)
- ✅ Webhook secret configured (non-test environments)
- ✅ Rate limit configuration valid (all limits > 0)
- ✅ Security headers configuration checked

**Failure**: Pipeline fails if security checks fail.

### 6. Test Execution

**Command**: `pytest tests/ -v --tb=short`

**What Runs**:
- All unit tests
- All end-to-end tests
- Ledger invariant tests
- Compliance workflow tests
- Security tests

**Coverage**: Optional coverage report (does not fail pipeline)

### 7. Ledger Invariant Verification

**Command**: `pytest tests/test_e2e_deposit_flow.py tests/test_e2e_rejection_flow.py tests/test_e2e_investment_flow.py -v`

**Purpose**: Explicitly verify that ledger invariants are maintained:
- Double-entry accounting (sum credits == sum debits)
- LedgerEntry immutability
- Transaction status derivation
- Audit trail completeness

**Failure**: Pipeline fails on any ledger invariant violation.

---

## Running CI Locally

### Prerequisites

1. **Docker** (for PostgreSQL and Redis services)
2. **Python 3.12**
3. **PostgreSQL client tools** (optional, for manual DB operations)

### Option 1: Using Docker Compose

```bash
# Start services
cd infra
docker-compose up -d postgres redis

# Set environment variables
export ENV=test
export DATABASE_URL="postgresql://vancelian:vancelian_password@localhost:5432/vancelian_core_test"
export REDIS_URL="redis://localhost:6379/1"
export SECRET_KEY="test-secret-key-min-32-chars-for-local-testing"
export ZAND_WEBHOOK_SECRET="test-webhook-secret"
export LOG_LEVEL=INFO

# Run migrations
cd ../backend
alembic upgrade head

# Run tests
pytest tests/ -v
```

### Option 2: Manual Service Setup

```bash
# Start PostgreSQL (if not using Docker)
# Create test database
createdb vancelian_core_test

# Start Redis (if not using Docker)
redis-server --port 6379

# Follow Option 1 steps for environment and tests
```

### Option 3: Run Individual CI Steps

```bash
cd backend

# 1. Security checks
python scripts/security_check.py

# 2. Migration safety check
python scripts/check_migrations.py

# 3. Run tests
pytest tests/ -v

# 4. Run ledger invariant tests
pytest tests/test_e2e_deposit_flow.py tests/test_e2e_rejection_flow.py tests/test_e2e_investment_flow.py -v
```

---

## Environment Separation

### Test Environment

**Used in**: CI pipeline, local testing

**Characteristics**:
- Isolated test database (`vancelian_core_test`)
- Test Redis instance (DB 1)
- Test secrets allowed
- Logging level: INFO

**Configuration**:
- `ENV=test`
- Separate database and Redis from development/production

### Development Environment

**Used in**: Local development

**Characteristics**:
- Development database
- Development Redis instance
- Local secrets (not committed)
- Logging level: DEBUG

**Configuration**:
- `ENV=development` or `ENV=local`

### Production Environment

**Used in**: Production deployments

**Characteristics**:
- Production database
- Production Redis instance
- **Strong secrets required** (no defaults)
- HSTS enabled (recommended)
- Logging level: INFO or WARNING

**Configuration**:
- `ENV=production` or `ENV=prod`
- Secrets from secure secret management

---

## Adding New CI Checks

### 1. Add Check Script

Create a script in `backend/scripts/`:

```python
#!/usr/bin/env python3
"""Your check script"""
import sys
# ... your check logic ...
sys.exit(0 if success else 1)
```

### 2. Add to Workflow

Edit `.github/workflows/ci.yml`:

```yaml
- name: Your new check
  working-directory: ./backend
  run: |
    python scripts/your_check.py
```

### 3. Test Locally

```bash
python backend/scripts/your_check.py
```

### 4. Verify in CI

Push changes and verify the check runs in GitHub Actions.

---

## Migration Safety

### Principles

- ✅ Migrations must work on empty database
- ✅ Migrations must be reversible (when possible)
- ✅ No data loss in production
- ✅ Migrations are tested in CI before merge
- ✅ Partial unique indexes are used for nullable unique constraints (e.g., `users.external_subject`)

### Check Script

**File**: `backend/scripts/check_migrations.py`

**What it does**:
1. Loads Alembic configuration
2. Checks migration heads exist
3. Verifies current database state
4. Tests migration upgrade on empty database

### Running Locally

```bash
cd backend
python scripts/check_migrations.py
```

---

## Security Baseline

### Check Script

**File**: `backend/scripts/security_check.py`

### Checks Performed

1. **Required Environment Variables**:
   - `DATABASE_URL`
   - `REDIS_URL`
   - `SECRET_KEY`

2. **Secrets Configuration**:
   - `SECRET_KEY` not using default value (in non-dev)
   - `SECRET_KEY` minimum length (32 chars)
   - `ZAND_WEBHOOK_SECRET` set (in non-dev)

3. **Rate Limiting**:
   - All rate limits > 0
   - Configuration loaded correctly

4. **Security Headers**:
   - HSTS configuration checked (warning in production if disabled)

### Running Locally

```bash
cd backend
ENV=test python scripts/security_check.py
```

---

## Pipeline Failure Scenarios

### Migration Failure

**Symptom**: Pipeline fails at "Run Alembic migrations" or "Verify migration safety"

**Causes**:
- Migration file syntax error
- Migration cannot be applied to empty DB
- Missing dependencies

**Fix**: Review migration files, test locally, fix migration code

### Test Failure

**Symptom**: Pipeline fails at "Run pytest" or "Verify ledger invariants"

**Causes**:
- Test code error
- Business logic change breaking tests
- Ledger invariant violation
- Database state issue

**Fix**: Run tests locally, fix test or code, ensure tests pass

### Security Check Failure

**Symptom**: Pipeline fails at "Security baseline checks"

**Causes**:
- Missing required environment variable
- Weak/default secret in non-test environment
- Invalid rate limit configuration

**Fix**: Review security configuration, update environment variables, fix settings

---

## Secrets Management

### In CI

**Test Environment**: Uses test secrets (committed, safe for CI)

**Production Deployments**: Use GitHub Secrets or secure secret management:
- `SECRET_KEY`
- `ZAND_WEBHOOK_SECRET`
- Database credentials
- Redis credentials

### Never Commit

- Production secrets
- Real webhook secrets
- Database passwords
- API keys

### GitHub Secrets Setup

1. Go to repository Settings → Secrets and variables → Actions
2. Add secrets:
   - `PROD_SECRET_KEY`
   - `PROD_ZAND_WEBHOOK_SECRET`
   - `PROD_DATABASE_URL`
   - etc.

3. Use in deployment workflows (not CI):
```yaml
env:
  SECRET_KEY: ${{ secrets.PROD_SECRET_KEY }}
```

---

## Pipeline Output

### Success

All steps complete successfully:
- ✅ Migrations applied
- ✅ Security checks passed
- ✅ All tests passed
- ✅ Ledger invariants verified

### Failure

Pipeline fails fast on first error:
- Stops at failing step
- Provides error output
- No subsequent steps run

---

## Troubleshooting

### PostgreSQL Connection Failed

**Check**: Service health in workflow
**Fix**: Verify PostgreSQL service is running, check connection string

### Redis Connection Failed

**Check**: Service health in workflow
**Fix**: Verify Redis service is running, check connection string

### Migration Errors

**Check**: Migration files syntax
**Fix**: Test migrations locally, review Alembic configuration

### Test Timeouts

**Check**: Test execution time
**Fix**: Optimize slow tests, increase timeout if needed

---

## Best Practices

1. **Always test locally** before pushing
2. **Keep migrations small** and focused
3. **Never skip security checks** in CI
4. **Review CI output** before merging
5. **Fix CI failures immediately** - don't let them accumulate

---

**Last Updated**: 2025-12-18

