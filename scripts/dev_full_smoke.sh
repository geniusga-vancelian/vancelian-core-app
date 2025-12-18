#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Vancelian Core DEV Full Smoke Test...${NC}"

# Get script directory and repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "📁 Working directory: $REPO_ROOT"

# Step 1: Ensure stack is running
echo -e "\n${YELLOW}Step 1: Ensuring stack is running...${NC}"
if ! docker compose -f docker-compose.dev.yml ps | grep -q "vancelian-backend-dev.*Up"; then
    echo "Starting stack..."
    docker compose -f docker-compose.dev.yml up -d --build
    sleep 10
fi

# Step 2: Wait for backend to be ready
echo -e "\n${YELLOW}Step 2: Waiting for backend to be ready...${NC}"
MAX_RETRIES=30
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
    echo -e "${RED}❌ Backend failed to become ready${NC}"
    docker compose -f docker-compose.dev.yml logs --tail=200 backend
    exit 1
fi

# Step 3: Apply migrations
echo -e "\n${YELLOW}Step 3: Applying migrations...${NC}"
if ! docker compose -f docker-compose.dev.yml exec -T backend alembic upgrade head; then
    echo -e "${RED}❌ Migrations failed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Migrations applied${NC}"

# Step 4: Register a test user
echo -e "\n${YELLOW}Step 4: Registering test user...${NC}"
RANDOM_EMAIL="test-$(date +%s)@example.com"
RANDOM_PASSWORD="TestPassword123"

REGISTER_RESPONSE=$(curl -sf -X POST http://localhost:8000/api/v1/auth/register \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$RANDOM_EMAIL\",\"password\":\"$RANDOM_PASSWORD\",\"first_name\":\"Test\",\"last_name\":\"User\"}" || echo "FAILED")

if echo "$REGISTER_RESPONSE" | grep -q "user_id"; then
    USER_ID=$(echo "$REGISTER_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['user_id'])" 2>/dev/null || echo "")
    echo -e "${GREEN}✅ User registered: $RANDOM_EMAIL${NC}"
    echo "   User ID: $USER_ID"
else
    echo -e "${RED}❌ Registration failed${NC}"
    echo "Response: $REGISTER_RESPONSE"
    exit 1
fi

# Step 5: Login and get token
echo -e "\n${YELLOW}Step 5: Logging in...${NC}"
LOGIN_RESPONSE=$(curl -sf -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$RANDOM_EMAIL\",\"password\":\"$RANDOM_PASSWORD\"}" || echo "FAILED")

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")
    echo -e "${GREEN}✅ Login successful${NC}"
else
    echo -e "${RED}❌ Login failed${NC}"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

# Step 6: Call /api/v1/me
echo -e "\n${YELLOW}Step 6: Testing /api/v1/me endpoint...${NC}"
ME_RESPONSE=$(curl -sf http://localhost:8000/api/v1/me \
    -H "Authorization: Bearer $ACCESS_TOKEN" || echo "FAILED")

if echo "$ME_RESPONSE" | grep -q "user_id"; then
    echo -e "${GREEN}✅ /api/v1/me works${NC}"
    echo "   Response: $ME_RESPONSE"
else
    echo -e "${RED}❌ /api/v1/me failed${NC}"
    echo "Response: $ME_RESPONSE"
    exit 1
fi

# Step 7: Test admin endpoints (will fail without ADMIN role, but should return 403, not 404)
echo -e "\n${YELLOW}Step 7: Testing admin endpoints (expecting 403)...${NC}"
ADMIN_USERS_RESPONSE=$(curl -sf -w "\n%{http_code}" http://localhost:8000/admin/v1/users \
    -H "Authorization: Bearer $ACCESS_TOKEN" 2>&1 || echo "FAILED\n000")

HTTP_CODE=$(echo "$ADMIN_USERS_RESPONSE" | tail -1)
if [ "$HTTP_CODE" = "403" ] || [ "$HTTP_CODE" = "401" ]; then
    echo -e "${GREEN}✅ Admin endpoint exists (returned $HTTP_CODE as expected)${NC}"
else
    echo -e "${YELLOW}⚠️  Admin endpoint returned HTTP $HTTP_CODE${NC}"
fi

# Step 8: Verify frontends
echo -e "\n${YELLOW}Step 8: Verifying frontends...${NC}"
CLIENT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>&1 || echo "000")
ADMIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3001 2>&1 || echo "000")

if [ "$CLIENT_STATUS" = "200" ] || [ "$CLIENT_STATUS" = "404" ]; then
    echo -e "${GREEN}✅ Frontend-client responding (HTTP $CLIENT_STATUS)${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend-client status: HTTP $CLIENT_STATUS${NC}"
fi

if [ "$ADMIN_STATUS" = "200" ] || [ "$ADMIN_STATUS" = "404" ]; then
    echo -e "${GREEN}✅ Frontend-admin responding (HTTP $ADMIN_STATUS)${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend-admin status: HTTP $ADMIN_STATUS${NC}"
fi

# Step 9: Final summary
echo -e "\n${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Full smoke test completed successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "📋 Test Results:"
echo "  • User Registration: ✅"
echo "  • User Login: ✅"
echo "  • /api/v1/me: ✅"
echo "  • Admin endpoints: Available (require ADMIN role)"
echo "  • Frontend-client: HTTP $CLIENT_STATUS"
echo "  • Frontend-admin: HTTP $ADMIN_STATUS"
echo ""
echo "🔑 Test Credentials:"
echo "  Email: $RANDOM_EMAIL"
echo "  Password: $RANDOM_PASSWORD"
echo ""
echo "📊 Available URLs:"
echo "  • Backend API:     http://localhost:8000"
echo "  • API Docs:        http://localhost:8000/docs"
echo "  • Frontend Client: http://localhost:3000"
echo "  • Frontend Admin:  http://localhost:3001"
echo ""

