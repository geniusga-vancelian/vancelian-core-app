# Database Roles

This directory contains SQL scripts for setting up database roles with least privilege access.

## Roles

### vancelian_readwrite
- **Purpose**: Application default role for normal operations
- **Permissions**: Full read-write access to all tables
- **Used by**: Backend application, migrations

### vancelian_readonly
- **Purpose**: Read-only access for reporting, analytics, backups
- **Permissions**: SELECT only on all tables
- **Used by**: Analytics tools, reporting dashboards, backup scripts

## Setup

### Initial Setup

1. Run role creation:
   ```bash
   psql -U postgres -d vancelian_core -f db/roles/01_create_roles.sql
   ```

2. Set passwords (if not using external secret management):
   ```sql
   ALTER ROLE vancelian_readwrite WITH PASSWORD 'your-secure-password';
   ALTER ROLE vancelian_readonly WITH PASSWORD 'your-secure-password';
   ```

3. Run migrations (to create tables)

4. Grant permissions:
   ```bash
   psql -U postgres -d vancelian_core -f db/roles/02_grant_permissions.sql
   ```

### Docker Compose

Roles are created automatically if SQL files are mounted in `/docker-entrypoint-initdb.d/`.

**Note**: Passwords must be set via environment variables or secret management.

## Usage

### Application Connection

Set `DATABASE_URL` to use readwrite role:
```
DATABASE_URL=postgresql://vancelian_readwrite:password@host:5432/vancelian_core
```

### Read-Only Connection

For reporting/analytics:
```
DATABASE_URL=postgresql://vancelian_readonly:password@host:5432/vancelian_core
```

## Password Rotation

To rotate passwords:

```sql
-- Rotate readwrite password
ALTER ROLE vancelian_readwrite WITH PASSWORD 'new-secure-password';

-- Rotate readonly password
ALTER ROLE vancelian_readonly WITH PASSWORD 'new-secure-password';
```

**Important**: Update application configuration and restart services after password rotation.

## Security Notes

- **Never commit passwords** in SQL scripts
- Use secret management (e.g., AWS Secrets Manager, HashiCorp Vault) for production
- Regularly rotate passwords
- Monitor role usage and permissions
- Review default privileges periodically


