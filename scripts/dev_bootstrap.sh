#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Vancelian Core DEV stack bootstrap...${NC}"

# Get script directory and repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "📁 Working directory: $REPO_ROOT"

# Step 1: Stop and remove containers (optionally remove volumes)
echo -e "\n${YELLOW}Step 1: Stopping existing containers...${NC}"
if [ "${RESET_DB:-0}" = "1" ]; then
  echo -e "${RED}⚠️  RESET_DB=1: Removing volumes (database will be reset)${NC}"
  docker compose -f docker-compose.dev.yml down -v || true
else
  echo -e "${GREEN}ℹ️  Keeping volumes (database preserved). Set RESET_DB=1 to reset.${NC}"
  docker compose -f docker-compose.dev.yml down || true
fi

# Step 2: Build and start services
echo -e "\n${YELLOW}Step 2: Building and starting services...${NC}"
docker compose -f docker-compose.dev.yml up -d --build

# Step 3: Wait for postgres to be healthy
echo -e "\n${YELLOW}Step 3: Waiting for PostgreSQL to be healthy...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker compose -f docker-compose.dev.yml exec -T postgres pg_isready -U vancelian > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "⏳ Waiting for PostgreSQL... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ PostgreSQL failed to become healthy after $MAX_RETRIES retries${NC}"
    docker compose -f docker-compose.dev.yml logs --tail=200 postgres
    exit 1
fi

# Step 4: Wait for backend to be ready (check /health endpoint)
echo -e "\n${YELLOW}Step 4: Waiting for backend to be ready...${NC}"
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "⏳ Waiting for backend... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Backend failed to become ready after $MAX_RETRIES retries${NC}"
    docker compose -f docker-compose.dev.yml logs --tail=200 backend
    exit 1
fi

# Step 5: Run Alembic migrations
echo -e "\n${YELLOW}Step 5: Running Alembic migrations...${NC}"
if ! docker compose -f docker-compose.dev.yml exec -T backend alembic upgrade head; then
    echo -e "${RED}❌ Alembic migrations failed${NC}"
    docker compose -f docker-compose.dev.yml logs --tail=200 backend
    exit 1
fi
echo -e "${GREEN}✅ Migrations completed successfully${NC}"

# Step 6: Verify backend health endpoints
echo -e "\n${YELLOW}Step 6: Verifying backend health endpoints...${NC}"

echo -n "Testing /health: "
HEALTH_RESPONSE=$(curl -sf http://localhost:8000/health 2>&1 || echo "FAILED")
if echo "$HEALTH_RESPONSE" | grep -q "status"; then
    echo -e "${GREEN}✅ OK${NC}"
    echo "  Response: $HEALTH_RESPONSE"
else
    echo -e "${RED}❌ FAILED${NC}"
    echo "  Response: $HEALTH_RESPONSE"
    docker compose -f docker-compose.dev.yml logs --tail=200 backend
    exit 1
fi

echo -n "Testing /ready: "
READY_RESPONSE=$(curl -sf http://localhost:8000/ready 2>&1 || echo "FAILED")
if echo "$READY_RESPONSE" | grep -q "status"; then
    echo -e "${GREEN}✅ OK${NC}"
    echo "  Response: $READY_RESPONSE"
else
    echo -e "${YELLOW}⚠️  /ready returned non-200 or invalid response${NC}"
    echo "  Response: $READY_RESPONSE"
fi

# Step 7: Verify frontend endpoints
echo -e "\n${YELLOW}Step 7: Verifying frontend endpoints...${NC}"

echo -n "Testing frontend (http://localhost:3000): "
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>&1 || echo "000")
if [ "$FRONTEND_STATUS" = "200" ] || [ "$FRONTEND_STATUS" = "404" ]; then
    echo -e "${GREEN}✅ Responding (HTTP $FRONTEND_STATUS)${NC}"
else
    echo -e "${YELLOW}⚠️  Unexpected status: HTTP $FRONTEND_STATUS${NC}"
fi

# Step 8: Final summary
echo -e "\n${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ DEV stack bootstrap completed successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "📋 Available endpoints:"
echo "  • Backend API:     http://localhost:8000"
echo "  • API Docs:        http://localhost:8000/docs"
echo "  • Health Check:    http://localhost:8000/health"
echo "  • Ready Check:     http://localhost:8000/ready"
echo "  • Frontend:        http://localhost:3000"
echo "  • Login:           http://localhost:3000/login"
echo "  • Admin Users:     http://localhost:3000/admin/users"
echo "  • Admin Compliance: http://localhost:3000/admin/compliance"
echo ""
echo "📊 Container status:"
docker compose -f docker-compose.dev.yml ps
echo ""

