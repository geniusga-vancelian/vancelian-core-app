#!/bin/bash
# Test SQLAlchemy Offer↔Media relations after cleanup

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 TEST SQLALCHEMY OFFER↔MEDIA RELATIONS"
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
    echo "   Response: $HEALTH_BODY"
else
    echo "   ❌ Health check failed (HTTP $HEALTH_CODE)"
    echo "   Response: $HEALTH_BODY"
    exit 1
fi

echo ""
echo "3️⃣  Testing /api/v1/offers (list offers)"
OFFERS_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $(docker compose -f docker-compose.dev.yml exec -T backend python -c "from app.auth.jwt import create_dev_token; print(create_dev_token('user@example.com', ['USER']))" 2>/dev/null || echo 'test-token')" \
    "${BASE_URL}/api/v1/offers?limit=5" || echo "ERROR")
OFFERS_CODE=$(echo "$OFFERS_RESPONSE" | tail -n 1)
OFFERS_BODY=$(echo "$OFFERS_RESPONSE" | head -n -1)

if [ "$OFFERS_CODE" = "200" ]; then
    echo "   ✅ Offers list passed (HTTP $OFFERS_CODE)"
    OFFER_COUNT=$(echo "$OFFERS_BODY" | grep -o '"id"' | wc -l || echo "0")
    echo "   Found $OFFER_COUNT offers"
else
    echo "   ❌ Offers list failed (HTTP $OFFERS_CODE)"
    echo "   Response: $OFFERS_BODY"
    exit 1
fi

echo ""
echo "4️⃣  Testing /api/v1/offers/{id} (get offer detail)"
# Try to get first offer ID from list
FIRST_OFFER_ID=$(echo "$OFFERS_BODY" | grep -o '"id":"[^"]*"' | head -n 1 | cut -d'"' -f4 || echo "")

if [ -n "$FIRST_OFFER_ID" ]; then
    DETAIL_RESPONSE=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer $(docker compose -f docker-compose.dev.yml exec -T backend python -c "from app.auth.jwt import create_dev_token; print(create_dev_token('user@example.com', ['USER']))" 2>/dev/null || echo 'test-token')" \
        "${BASE_URL}/api/v1/offers/${FIRST_OFFER_ID}" || echo "ERROR")
    DETAIL_CODE=$(echo "$DETAIL_RESPONSE" | tail -n 1)
    DETAIL_BODY=$(echo "$DETAIL_RESPONSE" | head -n -1)
    
    if [ "$DETAIL_CODE" = "200" ]; then
        echo "   ✅ Offer detail passed (HTTP $DETAIL_CODE)"
        echo "   Offer ID: $FIRST_OFFER_ID"
    else
        echo "   ❌ Offer detail failed (HTTP $DETAIL_CODE)"
        echo "   Response: $DETAIL_BODY"
        exit 1
    fi
else
    echo "   ⚠️  No offers found, skipping detail test"
fi

echo ""
echo "5️⃣  Checking backend logs for SQLAlchemy errors..."
ERROR_COUNT=$(docker compose -f docker-compose.dev.yml logs backend 2>&1 | grep -i "ambiguous foreign keys\|Could not determine\|InvalidRequestError" | wc -l || echo "0")

if [ "$ERROR_COUNT" -eq 0 ]; then
    echo "   ✅ No SQLAlchemy relationship errors found"
else
    echo "   ❌ Found $ERROR_COUNT SQLAlchemy relationship errors:"
    docker compose -f docker-compose.dev.yml logs backend 2>&1 | grep -i "ambiguous foreign keys\|Could not determine\|InvalidRequestError" | tail -5
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ALL TESTS PASSED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

