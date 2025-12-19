#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/gael/Desktop/VancelianAPP/vancelian-core-app"
if [ "$(pwd)" != "$ROOT" ]; then
  echo "❌ Repo guard failed: expected $ROOT, got $(pwd)"
  exit 1
fi

API="http://localhost:8000"
ORIGIN="http://localhost:3001"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CORS CHECK - Admin Presign Endpoint"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test OPTIONS preflight for admin presign endpoint
echo "1️⃣  Testing OPTIONS preflight for /admin/v1/offers/{id}/uploads/presign"
echo "   Origin: $ORIGIN"
echo ""

RESPONSE=$(curl -s -i -X OPTIONS \
  -H "Origin: $ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Authorization,Content-Type" \
  "$API/admin/v1/offers/00000000-0000-0000-0000-000000000000/uploads/presign" 2>&1)

echo "$RESPONSE" | head -20
echo ""

# Check for CORS headers
if echo "$RESPONSE" | grep -qi "access-control-allow-origin"; then
  echo "✅ Access-Control-Allow-Origin header found"
  echo "$RESPONSE" | grep -i "access-control-allow-origin"
else
  echo "❌ Access-Control-Allow-Origin header MISSING"
fi

if echo "$RESPONSE" | grep -qi "access-control-allow-methods"; then
  echo "✅ Access-Control-Allow-Methods header found"
  echo "$RESPONSE" | grep -i "access-control-allow-methods"
else
  echo "❌ Access-Control-Allow-Methods header MISSING"
fi

if echo "$RESPONSE" | grep -qi "access-control-allow-credentials"; then
  echo "✅ Access-Control-Allow-Credentials header found"
  echo "$RESPONSE" | grep -i "access-control-allow-credentials"
else
  echo "⚠️  Access-Control-Allow-Credentials header not found (may be default)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CORS CHECK - Admin Offers Endpoint"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "2️⃣  Testing OPTIONS preflight for /admin/v1/offers"
RESPONSE2=$(curl -s -i -X OPTIONS \
  -H "Origin: $ORIGIN" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization" \
  "$API/admin/v1/offers" 2>&1)

echo "$RESPONSE2" | head -15
echo ""

if echo "$RESPONSE2" | grep -qi "access-control-allow-origin"; then
  echo "✅ Access-Control-Allow-Origin header found"
else
  echo "❌ Access-Control-Allow-Origin header MISSING"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "If Access-Control-Allow-Origin headers are present → CORS is configured correctly"
echo "If missing → check backend logs and CORS middleware configuration"

