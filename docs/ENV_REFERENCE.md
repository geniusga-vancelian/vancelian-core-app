# Environment Variables Reference

This document lists all environment variables used across the Vancelian application.

## Frontend Variables

### frontend-admin & frontend-client

| Variable | Required | Default (Dev) | Description |
|----------|----------|---------------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | **Yes** (Prod) | `http://localhost:8000` (Dev only) | Base URL for API requests |
| `NEXT_PUBLIC_ADMIN_API_BASE_URL` | No | Falls back to `NEXT_PUBLIC_API_BASE_URL` | Admin-specific API base URL (optional override) |

**Note:** In production, `NEXT_PUBLIC_API_BASE_URL` MUST be set. The fallback to `localhost:8000` only works in development and will show a console warning.

## Backend Variables

### Core Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENV` | No | `local` | Environment name (local, staging, prod) |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `DEV_MODE` | No | `false` | Enable dev-only endpoints (⚠️ NEVER in production) |

### Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | **Yes** | - | PostgreSQL connection string |

### Redis

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | **Yes** | - | Redis connection string |

### Security

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | **Yes** | - | Application secret key (min 32 chars) |
| `JWT_SECRET` | No | - | JWT secret for HS256 (dev only) |
| `JWT_ALGORITHM` | No | `HS256` | JWT algorithm (HS256 for dev, RS256 for prod) |
| `ZAND_WEBHOOK_SECRET` | No | - | HMAC secret for ZAND webhook verification |

### CORS

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CORS_ENABLED` | No | `true` | Enable CORS middleware |
| `CORS_ALLOW_ORIGINS` | **Yes** (if CORS_ENABLED) | - | Comma-separated list of allowed origins |
| `CORS_ALLOW_METHODS` | No | `*` | Comma-separated list of allowed HTTP methods |
| `CORS_ALLOW_HEADERS` | No | `*` | Comma-separated list of allowed headers |
| `CORS_ALLOW_CREDENTIALS` | No | `true` | Allow credentials (cookies, Authorization headers) |
| `ALLOWED_ORIGINS` | No | - | Legacy: comma-separated origins (for backward compatibility) |

**Example:**
```bash
CORS_ALLOW_ORIGINS=http://localhost:3000,http://localhost:3001,https://app.example.com
```

### Storage (S3/R2)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `STORAGE_PROVIDER` | No | `s3` | Storage provider: `s3` (AWS/R2), `none` |
| `S3_BUCKET` | **Yes** (if storage enabled) | - | S3/R2 bucket name |
| `S3_ACCESS_KEY_ID` | **Yes** (if storage enabled) | - | S3/R2 access key ID |
| `S3_SECRET_ACCESS_KEY` | **Yes** (if storage enabled) | - | S3/R2 secret access key |
| `S3_ENDPOINT_URL` | **Yes** (for R2) | - | R2 endpoint URL (e.g., `https://<account-id>.r2.cloudflarestorage.com`) |
| `S3_REGION` | No | `auto` | Region (`auto` for R2, or AWS region like `eu-west-1`) |
| `S3_PUBLIC_BASE_URL` | No | - | Public CDN base URL (optional, for direct access) |
| `S3_PRESIGN_EXPIRES_SECONDS` | No | `900` | Presigned URL expiration (seconds) |
| `S3_KEY_PREFIX` | No | `offers` | Prefix for offer media object keys |
| `ARTICLES_KEY_PREFIX` | No | `articles` | Prefix for article media object keys |
| `S3_MAX_DOCUMENT_SIZE` | No | `52428800` | Max document size (bytes, default: 50MB) |
| `S3_MAX_VIDEO_SIZE` | No | `209715200` | Max video size (bytes, default: 200MB) |
| `S3_MAX_IMAGE_SIZE` | No | `10485760` | Max image size (bytes, default: 10MB) |

**Storage is enabled** when:
- `STORAGE_PROVIDER != "none"` AND
- `S3_BUCKET` is set AND
- `S3_ACCESS_KEY_ID` is set AND
- `S3_SECRET_ACCESS_KEY` is set AND
- (For R2) `S3_ENDPOINT_URL` is set

### OIDC / JWT (Production)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OIDC_ISSUER_URL` | **Yes** (Prod) | - | OIDC issuer URL (e.g., `https://auth.zitadel.cloud`) |
| `OIDC_AUDIENCE` | **Yes** (Prod) | - | Expected audience (client ID) |
| `OIDC_JWKS_URL` | No | - | Explicit JWKS URL (if not provided, derived from issuer) |
| `OIDC_ALGORITHMS` | No | `RS256` | Allowed JWT algorithms (comma-separated) |
| `OIDC_REQUIRED_SCOPES` | No | - | Required scopes (comma-separated) |
| `OIDC_CLOCK_SKEW_SECONDS` | No | `60` | Clock skew tolerance (seconds) |
| `OIDC_ROLE_CLAIM_PATHS` | No | `realm_access.roles,resource_access.{audience}.roles,roles` | Paths to extract roles from JWT |

### Observability

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `METRICS_PUBLIC` | No | `false` | Make `/metrics` endpoint public |
| `METRICS_TOKEN` | No | - | Static token for `/metrics` access (if `METRICS_PUBLIC=false`) |

### Rate Limiting

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RL_WEBHOOK_PER_MIN` | No | `120` | Rate limit for webhook endpoints (requests/min) |
| `RL_ADMIN_PER_MIN` | No | `60` | Rate limit for admin endpoints (requests/min) |
| `RL_API_PER_MIN` | No | `120` | Rate limit for API endpoints (requests/min) |

## Development Setup

### `.env.dev` (Local Development)

Create `.env.dev` in the repository root (already in `.gitignore`):

```bash
# API Configuration
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# CORS
CORS_ALLOW_ORIGINS=http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001

# Storage (R2)
S3_BUCKET=your-bucket-name
S3_ACCESS_KEY_ID=your-access-key-id
S3_SECRET_ACCESS_KEY=your-secret-access-key
S3_ENDPOINT_URL=https://your-account-id.r2.cloudflarestorage.com
S3_REGION=auto

# Database
DATABASE_URL=postgresql://vancelian:vancelian_password@postgres:5432/vancelian_core

# Redis
REDIS_URL=redis://redis:6379/0

# Security (dev only - change in production)
SECRET_KEY=dev-secret-key-min-32-chars-for-local-development-only
JWT_SECRET=dev_secret_change_me
```

### `docker-compose.dev.yml`

The `docker-compose.dev.yml` file sets default values for development. These can be overridden by `.env.dev`:

- `NEXT_PUBLIC_API_BASE_URL` is set in the frontend services
- `CORS_ALLOW_ORIGINS` is set in the backend service
- Other variables are loaded from `.env.dev` via `env_file`

## Production Setup

### Required Variables

**Frontend (Next.js):**
- `NEXT_PUBLIC_API_BASE_URL` - **MUST be set** (no fallback in production)

**Backend:**
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - Application secret (min 32 chars)
- `CORS_ALLOW_ORIGINS` - Comma-separated list of allowed origins
- `OIDC_ISSUER_URL` - OIDC issuer URL (or `JWT_SECRET` for dev mode)
- `OIDC_AUDIENCE` - Expected audience

**Storage (if using):**
- `S3_BUCKET`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`
- `S3_ENDPOINT_URL` (for R2)
- `S3_REGION`

### Validation

The backend validates required environment variables at startup:
- If `CORS_ENABLED=true` but `CORS_ALLOW_ORIGINS` is empty → Warning (CORS disabled)
- If storage is enabled but required S3 vars are missing → Storage disabled (returns 412 on storage operations)

## Security Notes

1. **Never commit** `.env.dev` or any file containing secrets
2. **Rotate secrets** regularly in production
3. **Use different secrets** for dev/staging/prod
4. **Limit API token permissions** (for R2/S3) to minimum required
5. **Use CDN** (`S3_PUBLIC_BASE_URL`) for public assets when possible

## Testing

Run the anti-hardcode audit:

```bash
./scripts/check_env_hardcode.sh
```

This script checks for hardcoded URLs, endpoints, and secrets in the codebase (excluding acceptable fallbacks in config files and docker-compose.dev.yml).

