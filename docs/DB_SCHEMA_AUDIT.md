# Database Schema Audit

## Overview

The database schema audit script (`scripts/audit_db_schema.py`) automatically verifies that the PostgreSQL database schema matches the expected structure, particularly after Alembic migrations for Marketing V1.1.

## What It Checks

### A) Alembic Migrations
- Verifies that the `alembic_version` table exists
- Checks that a current revision is set
- **FAIL** if migrations are not applied

### B) Table `offers`
Verifies existence of required columns:
- `id` (UUID, primary key)
- `cover_media_id` (UUID, nullable) - FK to `offer_media.id`
- `promo_video_media_id` (UUID, nullable) - FK to `offer_media.id`
- `marketing_title` (text/varchar, nullable)
- `marketing_subtitle` (text/varchar, nullable)
- `location_label` (text/varchar, nullable)
- `marketing_why` (JSONB, nullable)
- `marketing_highlights` (JSONB, nullable)
- `marketing_breakdown` (JSONB, nullable)
- `marketing_metrics` (JSONB, nullable)

### C) Table `offer_media`
Verifies existence of required columns:
- `id` (UUID, primary key)
- `offer_id` (UUID, FK to `offers.id`)
- `type` (enum/text) - image/video/document
- `key` (text/varchar) - S3/R2 storage key
- `mime_type` (text/varchar)
- `size_bytes` (bigint/integer)
- `created_at` (timestamp)

### D) Foreign Keys
Verifies the following foreign key constraints:
1. `offer_media.offer_id` → `offers.id` (ON DELETE CASCADE or NO ACTION)
2. `offers.cover_media_id` → `offer_media.id` (ON DELETE SET NULL or NO ACTION)
3. `offers.promo_video_media_id` → `offer_media.id` (ON DELETE SET NULL or NO ACTION)

### E) Indexes
Checks for recommended indexes:
- Index on `offer_media(offer_id)`
- Index on `offers(cover_media_id)` (WARN if missing)
- Index on `offers(promo_video_media_id)` (WARN if missing)

### F) Sanity Checks
- Displays PostgreSQL version
- Shows current database name
- Lists all tables and their column counts
- Verifies DATABASE_URL connection

## Usage

### Option 1: Using Make (Recommended)

```bash
make audit-db
```

### Option 2: Direct Script Execution

**Inside Docker container:**
```bash
docker compose -f docker-compose.dev.yml exec backend python3 scripts/audit_db_schema.py
```

**Locally (if DATABASE_URL is set):**
```bash
export DATABASE_URL=postgresql://vancelian:vancelian_password@localhost:5432/vancelian_core
python3 scripts/audit_db_schema.py
```

### Option 3: Using Bash Wrapper

```bash
./scripts/audit_db_schema.sh
```

## Output

The script produces:

1. **Console Output**: Human-readable report with:
   - Overall status (PASS/FAIL)
   - Individual check results (PASS/FAIL/WARN)
   - Summary counts
   - Details for each check

2. **JSON Report**: Saved to `reports/db_schema_audit.json` with:
   - Timestamp
   - Database information
   - All check results
   - Summary statistics

## Exit Codes

- `0`: All checks passed (PASS)
- `1`: One or more checks failed (FAIL)

## What to Do If Audit Fails

### 1. Migrations Not Applied

**Error:** `alembic_version table does not exist` or `No Alembic revision found`

**Solution:**
```bash
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
```

Then re-run the audit:
```bash
make audit-db
```

### 2. Missing Tables or Columns

**Error:** `Table 'offers' does not exist` or `Missing columns: cover_media_id, ...`

**Solution:**
1. Check that migrations are applied:
   ```bash
   docker compose -f docker-compose.dev.yml exec backend alembic current
   docker compose -f docker-compose.dev.yml exec backend alembic heads
   ```

2. If migrations are not up to date:
   ```bash
   docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
   ```

3. If migrations are up to date but columns are missing:
   - Check the migration files in `backend/alembic/versions/`
   - Verify that the migration adding Marketing V1.1 fields has been applied
   - Manually inspect the database:
     ```bash
     docker compose -f docker-compose.dev.yml exec postgres psql -U vancelian -d vancelian_core -c "\d offers"
     ```

### 3. Missing Foreign Keys

**Error:** `Missing foreign keys: offers.cover_media_id -> offer_media.id`

**Solution:**
1. Check if the migration that adds the FK has been applied
2. If the migration exists but FK is missing, you may need to:
   - Drop and recreate the constraint
   - Or manually add it:
     ```sql
     ALTER TABLE offers 
     ADD CONSTRAINT fk_offers_cover_media_id 
     FOREIGN KEY (cover_media_id) 
     REFERENCES offer_media(id) 
     ON DELETE SET NULL;
     ```

### 4. Missing Indexes (WARN)

**Warning:** `Recommended indexes missing: offers.cover_media_id`

**Solution:**
Indexes are recommended but not critical. If you want to add them:
```sql
CREATE INDEX idx_offers_cover_media_id ON offers(cover_media_id);
CREATE INDEX idx_offers_promo_video_media_id ON offers(promo_video_media_id);
```

Or create a new Alembic migration:
```bash
docker compose -f docker-compose.dev.yml exec backend alembic revision --autogenerate -m "add_indexes_offers_media"
```

## Manual Verification

If you want to manually verify the schema:

```bash
# Connect to database
docker compose -f docker-compose.dev.yml exec postgres psql -U vancelian -d vancelian_core

# List all tables
\dt

# Describe offers table
\d offers

# Describe offer_media table
\d offer_media

# List foreign keys
SELECT 
    tc.table_name, 
    kcu.column_name, 
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_schema = 'public';

# Check Alembic version
SELECT * FROM alembic_version;
```

## Integration with CI/CD

You can integrate the audit into your CI/CD pipeline:

```yaml
# Example GitHub Actions
- name: Audit Database Schema
  run: |
    docker compose -f docker-compose.dev.yml exec backend python3 scripts/audit_db_schema.py
```

Or in a Makefile target:

```makefile
ci-audit: migrate audit-db
	@echo "Migrations applied and schema audited"
```

## Troubleshooting

### Connection Issues

If you get connection errors:
1. Verify DATABASE_URL is set correctly
2. Check that PostgreSQL container is running:
   ```bash
   docker compose -f docker-compose.dev.yml ps postgres
   ```
3. Test connection manually:
   ```bash
   docker compose -f docker-compose.dev.yml exec postgres psql -U vancelian -d vancelian_core -c "SELECT 1;"
   ```

### Script Dependencies

If you get import errors:
```bash
# Install dependencies in backend container
docker compose -f docker-compose.dev.yml exec backend pip install psycopg[binary] sqlalchemy
```

## Related Documentation

- [Alembic Migrations](../backend/alembic/README.md)
- [Database Schema](../docs/architecture.md#database-schema)
- [Marketing V1.1 Implementation](../docs/MARKETING_V1_1.md)

