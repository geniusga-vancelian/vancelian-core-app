#!/bin/bash
# Test CORS configuration for backend

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 TEST CORS CONFIGURATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

BASE_URL="http://localhost:8000"

echo "1️⃣  Testing CORS debug endpoint (GET /admin/v1/debug/cors)"
echo "   Origin: http://localhost:3001"
echo ""
curl -i -H "Origin: http://localhost:3001" \
     -H "Authorization: Bearer $(docker compose -f docker-compose.dev.yml exec -T backend python -c "from app.auth.jwt import create_dev_token; print(create_dev_token('admin@example.com', ['ADMIN']))" 2>/dev/null || echo 'test-token')" \
     "${BASE_URL}/admin/v1/debug/cors" 2>/dev/null | head -n 30
echo ""
echo ""

echo "2️⃣  Testing CORS preflight (OPTIONS /admin/v1/offers)"
echo "   Origin: http://localhost:3001"
echo "   Method: GET"
echo ""
curl -i -X OPTIONS \
     -H "Origin: http://localhost:3001" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: Authorization,Content-Type" \
     "${BASE_URL}/admin/v1/offers" 2>/dev/null | head -n 40
echo ""
echo ""

echo "3️⃣  Testing CORS actual request (GET /admin/v1/offers)"
echo "   Origin: http://localhost:3001"
echo ""
curl -i -H "Origin: http://localhost:3001" \
     -H "Authorization: Bearer $(docker compose -f docker-compose.dev.yml exec -T backend python -c "from app.auth.jwt import create_dev_token; print(create_dev_token('admin@example.com', ['ADMIN']))" 2>/dev/null || echo 'test-token')" \
     "${BASE_URL}/admin/v1/offers" 2>/dev/null | head -n 30
echo ""
echo ""

echo "✅ CORS tests completed"
echo ""
echo "Expected headers in responses:"
echo "  - Access-Control-Allow-Origin: http://localhost:3001"
echo "  - Access-Control-Allow-Credentials: true"
echo "  - Access-Control-Allow-Methods: * (or specific methods)"
echo "  - Access-Control-Allow-Headers: * (or specific headers)"
echo ""

