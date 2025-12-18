# Production Release Checklist

This checklist ensures safe and reliable production deployments for Vancelian Core App.

## Pre-Deployment

### 1. Environment Variables

✅ **Required Variables**:
- [ ] `ENV=production`
- [ ] `POSTGRES_PASSWORD` (strong, unique)
- [ ] `POSTGRES_READWRITE_PASSWORD` (strong, unique)
- [ ] `POSTGRES_READONLY_PASSWORD` (strong, unique)
- [ ] `REDIS_PASSWORD` (strong, unique)
- [ ] `SECRET_KEY` (minimum 32 characters, strong random)
- [ ] `ZAND_WEBHOOK_SECRET` (from ZAND Bank, matches their configuration)
- [ ] `ALLOWED_ORIGINS` (production domains only)
- [ ] `OIDC_ISSUER_URL` (OIDC provider URL, e.g., `https://auth.zitadel.cloud`)
- [ ] `OIDC_AUDIENCE` (OIDC client ID / audience)

✅ **Optional Variables**:
- [ ] `LOG_LEVEL=INFO` (or WARNING for production)
- [ ] `ENABLE_HSTS=true` (if using HTTPS)
- [ ] `NGINX_HTTP_PORT` / `NGINX_HTTPS_PORT` (if custom ports)

**Verification**:
```bash
# Check all required variables are set
python backend/scripts/security_check.py
```

### 2. Database Preparation

✅ **Initial Setup**:
- [ ] PostgreSQL instance provisioned
- [ ] Database `vancelian_core` created
- [ ] Database roles created (`vancelian_readwrite`, `vancelian_readonly`)
- [ ] Role passwords set and stored securely
- [ ] Permissions granted (run `db/roles/02_grant_permissions.sql` after migrations)

✅ **Migrations**:
- [ ] All migrations reviewed
- [ ] Migrations tested on staging/test environment
- [ ] Backup of production database created
- [ ] Migration rollback plan prepared
- [ ] **Note**: `users.external_subject` uses partial unique index (WHERE external_subject IS NOT NULL) to allow multiple NULL values while ensuring non-NULL OIDC subjects are unique

**Commands**:
```bash
# Initialize database roles
psql -U postgres -d vancelian_core -f db/roles/01_create_roles.sql

# Set passwords (or use secret management)
psql -U postgres -d vancelian_core -c "ALTER ROLE vancelian_readwrite WITH PASSWORD '...';"
psql -U postgres -d vancelian_core -c "ALTER ROLE vancelian_readonly WITH PASSWORD '...';"

# Run migrations
cd backend
alembic upgrade head

# Verify migration applied correctly
psql -U postgres -d vancelian_core -c "\d users" | grep external_subject

# Grant permissions
psql -U postgres -d vancelian_core -f db/roles/02_grant_permissions.sql
```

**Migration Details**:
- `users.external_subject` column: nullable, indexed
- Partial unique index: `ix_users_external_subject_unique` (WHERE external_subject IS NOT NULL)
  - Allows multiple NULL values (users without OIDC subject)
  - Ensures uniqueness for non-NULL OIDC subjects
- No backfill required: `external_subject` is set on first authenticated OIDC request

### 3. Nginx Configuration

✅ **IP Whitelisting**:
- [ ] Admin endpoint IPs configured (`/admin/v1/*`)
- [ ] Webhook endpoint IPs configured (`/webhooks/v1/*`)
- [ ] IP whitelist tested
- [ ] Default behavior: **BLOCKED** (403) for non-whitelisted IPs

**Configuration**:
- Edit `nginx/default.conf`
- Update `geo $admin_allowed` and `geo $webhook_allowed` blocks
- Or use include files for dynamic IP management

✅ **Security Headers**:
- [ ] Nginx security headers verified
- [ ] HSTS enabled (if using HTTPS)
- [ ] SSL/TLS certificates configured (if using HTTPS)

### 4. Docker Configuration

✅ **Production Compose**:
- [ ] `.env.prod` created from `.env.prod.example`
- [ ] All secrets filled in (never commit `.env.prod`)
- [ ] Docker images built
- [ ] Volumes configured correctly
- [ ] Networks configured correctly

**Commands**:
```bash
# Copy example and fill in values
cp .env.prod.example .env.prod
# Edit .env.prod with actual values

# Build images
docker-compose -f docker-compose.prod.yml build

# Verify configuration
docker-compose -f docker-compose.prod.yml config
```

## Deployment

### 5. Migration Steps

✅ **Order of Operations**:
1. [ ] Backup production database
2. [ ] Start PostgreSQL (if not already running)
3. [ ] Start Redis (if not already running)
4. [ ] Run database migrations: `alembic upgrade head`
5. [ ] Verify migrations applied successfully
6. [ ] Start backend service
7. [ ] Start nginx service
8. [ ] Verify all services healthy

**Commands**:
```bash
# Start infrastructure services
docker-compose -f docker-compose.prod.yml up -d postgres redis

# Wait for services to be ready
docker-compose -f docker-compose.prod.yml exec postgres pg_isready
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping

# Run migrations
docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# Start all services
docker-compose -f docker-compose.prod.yml up -d
```

### 6. Smoke Tests

✅ **Health Checks**:
- [ ] `/health` returns 200 OK
- [ ] `/ready` returns 200 OK (checks DB + Redis connectivity)
- [ ] Response includes correct headers

**Commands**:
```bash
# Health check
curl http://localhost/health

# Readiness check
curl http://localhost/ready

# Verify headers
curl -I http://localhost/health
```

✅ **API Endpoints**:
- [ ] Public API endpoint accessible (`/api/v1/wallet`)
- [ ] Rate limiting works (test with multiple requests)
- [ ] Security headers present
- [ ] Error responses include trace_id

✅ **Admin Endpoints** (if whitelisted):
- [ ] Admin endpoint accessible from whitelisted IP
- [ ] Admin endpoint blocked from non-whitelisted IP (403)
- [ ] Rate limiting works

✅ **Webhook Endpoints** (if whitelisted):
- [ ] Webhook endpoint accessible from whitelisted IP
- [ ] Webhook endpoint blocked from non-whitelisted IP (403)
- [ ] Signature verification works

### 7. Logging Checks

✅ **Structured Logging**:
- [ ] Logs are structured JSON format
- [ ] Trace IDs present in all logs
- [ ] Log level appropriate (INFO for production)
- [ ] Logs include request context

**Commands**:
```bash
# Check backend logs
docker-compose -f docker-compose.prod.yml logs backend

# Check nginx logs
docker-compose -f docker-compose.prod.yml logs nginx

# Verify JSON structure
docker-compose -f docker-compose.prod.yml logs backend | jq .
```

✅ **Security Event Logging**:
- [ ] Security events logged (rate limits, webhook rejections)
- [ ] AuditLog entries created for critical actions
- [ ] No secrets exposed in logs

### 8. Security Checks

✅ **Webhook Security**:
- [ ] `ZAND_WEBHOOK_SECRET` configured correctly
- [ ] Signature verification tested (accept valid, reject invalid)
- [ ] Replay protection working (timestamp tolerance)
- [ ] Idempotency enforced (duplicate events handled)

**Test**:
```bash
# Test webhook with valid signature (requires actual signature calculation)
curl -X POST http://localhost/webhooks/v1/zand/deposit \
  -H "X-Zand-Signature: valid-signature" \
  -H "X-Zand-Timestamp: $(date +%s)" \
  -H "Content-Type: application/json" \
  -d '{"provider_event_id":"test","iban":"...","user_id":"...","amount":"1000.00","currency":"AED","occurred_at":"2025-12-18T10:00:00Z"}'
```

✅ **Rate Limiting**:
- [ ] Rate limits enforced (test exceeding limits)
- [ ] HTTP 429 returned with correct format
- [ ] Rate limit headers present (`X-RateLimit-*`)
- [ ] Different limits for different endpoint groups

**Test**:
```bash
# Test rate limiting
for i in {1..150}; do
  curl http://localhost/api/v1/wallet?currency=AED
done
# Should see 429 after limit exceeded
```

✅ **Access Control**:
- [ ] `/admin/v1/*` blocked from public (403)
- [ ] `/webhooks/v1/*` blocked from public (403)
- [ ] Whitelisted IPs can access protected endpoints
- [ ] RBAC stubs in place (ready for real auth integration)

### 9. Database Verification

✅ **Database Roles**:
- [ ] Application uses `vancelian_readwrite` role
- [ ] Read-only role available for reporting
- [ ] Permissions correct (readwrite has full access, readonly SELECT only)

**Verify**:
```sql
-- Check current role
SELECT current_user;

-- Test readonly access (should work)
\c vancelian_core vancelian_readonly
SELECT * FROM users LIMIT 1;

-- Test readonly write (should fail)
INSERT INTO users (id, email, status) VALUES (gen_random_uuid(), 'test', 'ACTIVE');
-- Expected: ERROR: permission denied
```

✅ **Ledger Integrity**:
- [ ] Double-entry accounting verified
- [ ] No orphaned ledger entries
- [ ] Account balances calculated correctly

## Post-Deployment

### 10. Monitoring

✅ **Service Health**:
- [ ] All services running (`docker-compose ps`)
- [ ] Health checks passing
- [ ] No error spikes in logs
- [ ] Response times acceptable

✅ **Resource Usage**:
- [ ] CPU usage normal
- [ ] Memory usage normal
- [ ] Database connections within limits
- [ ] Redis memory usage acceptable

### 11. Rollback Strategy

✅ **Prepared Rollback Plan**:
- [ ] Database backup available
- [ ] Previous application version tagged
- [ ] Rollback procedure documented
- [ ] Rollback tested in staging

**Rollback Steps** (if needed):
```bash
# 1. Stop services
docker-compose -f docker-compose.prod.yml down

# 2. Restore database backup (if needed)
# ... restore from backup ...

# 3. Deploy previous version
git checkout <previous-tag>
docker-compose -f docker-compose.prod.yml up -d

# 4. Verify rollback successful
curl http://localhost/health
```

### 12. Documentation

✅ **Release Notes**:
- [ ] Changes documented
- [ ] Migration notes documented
- [ ] Known issues documented
- [ ] Rollback procedure documented

## Production Run Commands

### Start Production Stack

```bash
# Ensure .env.prod is configured
cp .env.prod.example .env.prod
# Edit .env.prod with actual values

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Initialize Database Roles

```bash
# Create roles
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U postgres -d vancelian_core -f /docker-entrypoint-initdb.d/roles/01_create_roles.sql

# Set passwords (or use secret management)
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U postgres -d vancelian_core \
  -c "ALTER ROLE vancelian_readwrite WITH PASSWORD '...';" \
  -c "ALTER ROLE vancelian_readonly WITH PASSWORD '...';"

# Run migrations
docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# Grant permissions
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U postgres -d vancelian_core -f /docker-entrypoint-initdb.d/roles/02_grant_permissions.sql
```

### Verify Deployment

```bash
# Health check
curl http://localhost/health

# Readiness check
curl http://localhost/ready

# Check services
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs backend | tail -50
```

## Security Verification

### Default Protection

✅ **Verified**:
- `/admin/v1/*` → **BLOCKED by default** (403) unless IP whitelisted
- `/webhooks/v1/*` → **BLOCKED by default** (403) unless IP whitelisted
- Public endpoints (`/api/v1/*`, `/health`) → Accessible with rate limiting

### IP Whitelisting Options

1. **Static IPs in nginx config** (current approach):
   - Edit `nginx/default.conf`
   - Add IPs to `geo $admin_allowed` and `geo $webhook_allowed`
   - Restart nginx

2. **Dynamic via include file**:
   - Mount whitelist config file as volume
   - Update file without restarting (if using `include` directive)

3. **Environment-based config**:
   - Generate nginx config from environment variables
   - Use init container or entrypoint script

---

**Last Updated**: 2025-12-18

