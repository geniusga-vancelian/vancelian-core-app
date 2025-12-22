#!/bin/bash
# Test SQLAlchemy relationships after removing cover/promo ORM relations

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 TEST SQLALCHEMY RELATIONSHIPS (NO AMBIGUITY)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

BASE_URL="http://localhost:8000"

echo "1️⃣  Restarting backend..."
docker compose -f docker-compose.dev.yml restart backend
echo "   Waiting for backend to be ready..."
sleep 5

echo ""
echo "2️⃣  Testing /health endpoint"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/health" || echo "ERROR")
HEALTH_CODE=$(echo "$HEALTH_RESPONSE" | tail -n 1)
HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | head -n -1)

if [ "$HEALTH_CODE" = "200" ]; then
    echo "   ✅ Health check passed (HTTP $HEALTH_CODE)"
else
    echo "   ❌ Health check failed (HTTP $HEALTH_CODE)"
    echo "   Response: $HEALTH_BODY"
    exit 1
fi

echo ""
echo "3️⃣  Testing GET /admin/v1/offers (list offers)"
# Create a dev admin token (simplified - adjust if needed)
ADMIN_TOKEN=$(docker compose -f docker-compose.dev.yml exec -T backend python -c "
from app.auth.jwt import create_dev_token
print(create_dev_token('admin@example.com', ['ADMIN']))
" 2>/dev/null || echo "dev-admin-token")

OFFERS_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    "${BASE_URL}/admin/v1/offers?limit=5" || echo "ERROR")
OFFERS_CODE=$(echo "$OFFERS_RESPONSE" | tail -n 1)
OFFERS_BODY=$(echo "$OFFERS_RESPONSE" | head -n -1)

if [ "$OFFERS_CODE" = "200" ]; then
    echo "   ✅ Admin offers list passed (HTTP $OFFERS_CODE)"
    OFFER_COUNT=$(echo "$OFFERS_BODY" | grep -o '"id"' | wc -l || echo "0")
    echo "   Found $OFFER_COUNT offers"
else
    echo "   ❌ Admin offers list failed (HTTP $OFFERS_CODE)"
    echo "   Response: $OFFERS_BODY"
    exit 1
fi

echo ""
echo "4️⃣  Testing GET /admin/v1/offers/{id} (get offer detail)"
# Try to get first offer ID from list
FIRST_OFFER_ID=$(echo "$OFFERS_BODY" | grep -o '"id":"[^"]*"' | head -n 1 | cut -d'"' -f4 || echo "")

if [ -n "$FIRST_OFFER_ID" ]; then
    DETAIL_RESPONSE=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer ${ADMIN_TOKEN}" \
        "${BASE_URL}/admin/v1/offers/${FIRST_OFFER_ID}" || echo "ERROR")
    DETAIL_CODE=$(echo "$DETAIL_RESPONSE" | tail -n 1)
    DETAIL_BODY=$(echo "$DETAIL_RESPONSE" | head -n -1)
    
    if [ "$DETAIL_CODE" = "200" ]; then
        echo "   ✅ Admin offer detail passed (HTTP $DETAIL_CODE)"
        echo "   Offer ID: $FIRST_OFFER_ID"
    else
        echo "   ❌ Admin offer detail failed (HTTP $DETAIL_CODE)"
        echo "   Response: $DETAIL_BODY"
        exit 1
    fi
else
    echo "   ⚠️  No offers found, skipping detail test"
fi

echo ""
echo "5️⃣  Testing GET /api/v1/offers (public list)"
USER_TOKEN=$(docker compose -f docker-compose.dev.yml exec -T backend python -c "
from app.auth.jwt import create_dev_token
print(create_dev_token('user@example.com', ['USER']))
" 2>/dev/null || echo "dev-user-token")

PUBLIC_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer ${USER_TOKEN}" \
    "${BASE_URL}/api/v1/offers?limit=5" || echo "ERROR")
PUBLIC_CODE=$(echo "$PUBLIC_RESPONSE" | tail -n 1)
PUBLIC_BODY=$(echo "$PUBLIC_RESPONSE" | head -n -1)

if [ "$PUBLIC_CODE" = "200" ]; then
    echo "   ✅ Public offers list passed (HTTP $PUBLIC_CODE)"
else
    echo "   ❌ Public offers list failed (HTTP $PUBLIC_CODE)"
    echo "   Response: $PUBLIC_BODY"
    exit 1
fi

echo ""
echo "6️⃣  Checking backend logs for SQLAlchemy errors..."
ERROR_COUNT=$(docker compose -f docker-compose.dev.yml logs backend 2>&1 | grep -iE "InvalidRequestError|Could not determine|ambiguous foreign keys|AmbiguousForeignKeysError" | wc -l || echo "0")

if [ "$ERROR_COUNT" -eq 0 ]; then
    echo "   ✅ No SQLAlchemy relationship errors found"
else
    echo "   ❌ Found $ERROR_COUNT SQLAlchemy relationship errors:"
    docker compose -f docker-compose.dev.yml logs backend 2>&1 | grep -iE "InvalidRequestError|Could not determine|ambiguous foreign keys|AmbiguousForeignKeysError" | tail -5
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ALL TESTS PASSED - NO SQLALCHEMY AMBIGUITY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

