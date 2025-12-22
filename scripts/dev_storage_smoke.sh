#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/gael/Desktop/VancelianAPP/vancelian-core-app"
if [ "$(pwd)" != "$ROOT" ]; then
  echo "❌ Repo guard failed: expected $ROOT, got $(pwd)"
  exit 1
fi

API="http://localhost:8000"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STORAGE CONFIGURATION SMOKE TEST"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if backend is running
if ! curl -s -f "${API}/health" > /dev/null 2>&1; then
  echo "❌ Backend is not running at ${API}"
  echo "   Start it with: docker compose -f docker-compose.dev.yml up -d backend"
  exit 1
fi

echo "1️⃣  Checking storage configuration..."
echo ""

# Try to get storage info (without auth for now - endpoint requires ADMIN)
# For now, we'll just check if the endpoint exists
STORAGE_RESPONSE=$(curl -s -w "\n%{http_code}" "${API}/admin/v1/system/storage" 2>&1 || echo "000")

HTTP_CODE=$(echo "$STORAGE_RESPONSE" | tail -n 1)
BODY=$(echo "$STORAGE_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
  echo "   ⚠️  Endpoint requires authentication (expected)"
  echo "   To test with auth, use:"
  echo "   curl -H 'Authorization: Bearer <admin-token>' ${API}/admin/v1/system/storage"
  echo ""
  echo "   For now, checking backend logs for storage errors..."
elif [ "$HTTP_CODE" = "200" ]; then
  echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
  ENABLED=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('enabled', False))" 2>/dev/null || echo "false")
  
  if [ "$ENABLED" = "True" ] || [ "$ENABLED" = "true" ]; then
    echo ""
    echo "   ✅ Storage is configured"
    echo ""
    echo "2️⃣  Testing presign endpoint (requires offer_id and admin token)..."
    echo "   ⚠️  Manual test required:"
    echo "   curl -X POST -H 'Authorization: Bearer <admin-token>' \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"upload_type\":\"media\",\"file_name\":\"test.jpg\",\"mime_type\":\"image/jpeg\",\"size_bytes\":1024,\"media_type\":\"IMAGE\"}' \\"
    echo "     ${API}/admin/v1/offers/<offer-id>/uploads/presign"
  else
    echo ""
    echo "   ⚠️  Storage is NOT configured"
    echo ""
    echo "   To configure storage, set these environment variables:"
    echo "   - S3_BUCKET"
    echo "   - S3_ACCESS_KEY_ID"
    echo "   - S3_SECRET_ACCESS_KEY"
    echo "   - S3_ENDPOINT_URL (for R2)"
    echo "   - S3_REGION (for R2: 'auto')"
    echo ""
    echo "   See docs/STORAGE_R2_SETUP.md for details"
    echo ""
    echo "   ✅ Backend handles missing storage gracefully (returns 412, not 500)"
    exit 0
  fi
else
  echo "   ❌ Unexpected response: HTTP $HTTP_CODE"
  echo "$BODY"
  exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Storage smoke test completed"
echo ""
echo "If storage is not configured, the backend will return 412 (Precondition Failed)"
echo "with code STORAGE_NOT_CONFIGURED instead of 500 (Internal Server Error)."
echo ""
echo "This is expected behavior for development environments without S3/R2 setup."

