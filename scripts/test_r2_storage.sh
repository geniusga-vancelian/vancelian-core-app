#!/bin/bash
# Test script for R2 storage configuration
# Usage: ./scripts/test_r2_storage.sh [JWT_TOKEN] [OFFER_ID]

set -e

JWT=${1:-""}
OFFER_ID=${2:-""}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 R2 STORAGE TEST"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test 1: Health check
echo "1️⃣  Testing backend health..."
if curl -s -f http://localhost:8000/health > /dev/null; then
    echo "   ✅ Backend is healthy"
else
    echo "   ❌ Backend is not responding"
    exit 1
fi
echo ""

# Test 2: Storage status (without auth - should return 401 or show enabled=false)
echo "2️⃣  Testing storage status endpoint (no auth)..."
STORAGE_RESPONSE=$(curl -s http://localhost:8000/admin/v1/system/storage)
if echo "$STORAGE_RESPONSE" | grep -q "enabled"; then
    echo "   Response:"
    echo "$STORAGE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$STORAGE_RESPONSE"
else
    echo "   Response (likely 401): $STORAGE_RESPONSE"
fi
echo ""

# Test 3: Storage status (with auth)
if [ -n "$JWT" ]; then
    echo "3️⃣  Testing storage status endpoint (with auth)..."
    STORAGE_RESPONSE_AUTH=$(curl -s -H "Authorization: Bearer $JWT" \
        http://localhost:8000/admin/v1/system/storage)
    echo "   Response:"
    echo "$STORAGE_RESPONSE_AUTH" | python3 -m json.tool 2>/dev/null || echo "$STORAGE_RESPONSE_AUTH"
    echo ""
    
    # Check if enabled
    if echo "$STORAGE_RESPONSE_AUTH" | grep -q '"enabled": true'; then
        echo "   ✅ Storage is enabled"
    else
        echo "   ⚠️  Storage is not enabled (check .env.dev values)"
    fi
    echo ""
    
    # Test 4: Presign endpoint
    if [ -n "$OFFER_ID" ]; then
        echo "4️⃣  Testing presign endpoint..."
        PRESIGN_RESPONSE=$(curl -s -H "Authorization: Bearer $JWT" \
            -H "Content-Type: application/json" \
            -d '{
                "upload_type": "media",
                "file_name": "test.png",
                "mime_type": "image/png",
                "size_bytes": 1024,
                "media_type": "IMAGE"
            }' \
            "http://localhost:8000/admin/v1/offers/$OFFER_ID/uploads/presign")
        
        if echo "$PRESIGN_RESPONSE" | grep -q "upload_url"; then
            echo "   ✅ Presign successful"
            echo "   Response:"
            echo "$PRESIGN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$PRESIGN_RESPONSE"
        else
            echo "   ❌ Presign failed"
            echo "   Response:"
            echo "$PRESIGN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$PRESIGN_RESPONSE"
        fi
    else
        echo "4️⃣  Skipping presign test (no OFFER_ID provided)"
        echo "   Usage: $0 <JWT> <OFFER_ID>"
    fi
else
    echo "3️⃣  Skipping auth tests (no JWT provided)"
    echo "   Usage: $0 <JWT> [OFFER_ID]"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
