# 🔄 Reboot Runbook - Vancelian Dev Environment

## Quick Start (After Reboot)

```bash
cd /Users/gael/Desktop/VancelianAPP/vancelian-core-app
./scripts/dev_up.sh
```

That's it! The script will:
- ✅ Verify correct directory
- ✅ Check Docker is running
- ✅ Build and start all containers
- ✅ Wait for backend health check
- ✅ Wait for frontend to respond
- ✅ Print final URLs

## Expected URLs

After successful startup:
- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

## Frontend Source of Truth

**IMPORTANT**: Only `./frontend` is used for port 3000.

- ✅ `frontend/` → localhost:3000 (DEV frontend with TokenBar)
- ❌ `frontend-client/` → Archived (not used)
- ❌ `frontend-admin/` → Archived (not used)

See `docker-compose.dev.yml` for configuration.

## Status Check

```bash
./scripts/dev_status.sh
```

Shows:
- Container status
- Last 200 lines of backend logs
- Last 200 lines of frontend logs
- Health check results

## Troubleshooting

### Docker Not Running

```bash
# Start Docker Desktop, then:
./scripts/dev_up.sh
```

### Backend Won't Start

```bash
# Check backend logs
docker compose -f docker-compose.dev.yml logs backend

# Check database connection
docker compose -f docker-compose.dev.yml exec postgres psql -U vancelian -d vancelian_core -c "SELECT 1;"

# Restart backend
docker compose -f docker-compose.dev.yml restart backend
```

### Frontend Won't Start

```bash
# Check frontend logs
docker compose -f docker-compose.dev.yml logs frontend

# Rebuild frontend
docker compose -f docker-compose.dev.yml up -d --build frontend

# Check if port 3000 is in use
lsof -i :3000
```

### Port Already in Use

```bash
# Find what's using the port
lsof -i :3000  # Frontend
lsof -i :8000  # Backend
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis

# Stop conflicting services or change ports in docker-compose.dev.yml
```

### Database Issues

```bash
# Check PostgreSQL is running
docker compose -f docker-compose.dev.yml ps postgres

# Connect to database
docker compose -f docker-compose.dev.yml exec postgres psql -U vancelian -d vancelian_core

# Check migrations
docker compose -f docker-compose.dev.yml exec backend alembic current
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
```

### Complete Reset

```bash
# Stop everything
docker compose -f docker-compose.dev.yml down

# Remove volumes (⚠️ deletes data)
docker compose -f docker-compose.dev.yml down -v

# Start fresh
./scripts/dev_up.sh
```

### View All Logs

```bash
# Follow all logs
docker compose -f docker-compose.dev.yml logs -f

# Follow specific service
docker compose -f docker-compose.dev.yml logs -f backend
docker compose -f docker-compose.dev.yml logs -f frontend
```

### Rebuild Everything

```bash
# Stop
docker compose -f docker-compose.dev.yml down

# Rebuild and start
docker compose -f docker-compose.dev.yml up -d --build

# Or use the script
./scripts/dev_up.sh
```

## Common Issues

### Issue: "Wrong directory" error

**Solution**: Always run from `/Users/gael/Desktop/VancelianAPP/vancelian-core-app`

```bash
cd /Users/gael/Desktop/VancelianAPP/vancelian-core-app
./scripts/dev_up.sh
```

### Issue: Frontend shows "Loading..." forever

**Possible causes**:
1. Backend not responding
2. CORS issues
3. Next.js compilation error

**Check**:
```bash
# Check backend health
curl http://localhost:8000/health

# Check frontend logs
docker compose -f docker-compose.dev.yml logs frontend

# Check browser console for errors
```

### Issue: 401 Unauthorized errors

**Solution**: Login at http://localhost:3000/login

The frontend requires authentication for most endpoints.

## Manual Commands

If scripts don't work, manual steps:

```bash
# 1. Navigate to repo
cd /Users/gael/Desktop/VancelianAPP/vancelian-core-app

# 2. Start services
docker compose -f docker-compose.dev.yml up -d --build

# 3. Wait for health checks
curl http://localhost:8000/health
curl http://localhost:3000

# 4. Check status
docker compose -f docker-compose.dev.yml ps
```

## Archive Location

Unused frontends are archived in:
```
_archive_frontends/<timestamp>_unused_frontends/
```

To restore (if needed):
```bash
# List archives
ls -la _archive_frontends/

# Restore (example)
cp -r _archive_frontends/20251219_120000_unused_frontends/frontend-client ./
```

## Support

If issues persist:
1. Check `./scripts/dev_status.sh` output
2. Review logs: `docker compose -f docker-compose.dev.yml logs`
3. Verify Docker Desktop is running
4. Check disk space: `df -h`
5. Check Docker resources in Docker Desktop settings

