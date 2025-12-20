#!/bin/bash
# Runtime Environment Audit Script (Enhanced)
# Verifies that all required environment variables are set and services are running

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

FAILED=0
WARNINGS=0

echo "=================================================================================="
echo "🔍 RUNTIME ENVIRONMENT AUDIT"
echo "=================================================================================="
echo ""

# ============================================================================
# A) FILE CHECKS
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "A) FILE CHECKS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check .env.dev
if [ ! -f ".env.dev" ]; then
    echo "⚠️  WARN: .env.dev not found"
    WARNINGS=$((WARNINGS + 1))
else
    echo "✅ .env.dev found"
fi

# Check .env.dev in .gitignore
if grep -q "^\.env\.dev$" .gitignore 2>/dev/null || grep -q "^\.env\.dev" .gitignore 2>/dev/null; then
    echo "✅ .env.dev is in .gitignore"
else
    echo "❌ FAIL: .env.dev is NOT in .gitignore (security risk)"
    FAILED=1
fi

# Check ENV_REFERENCE.md
if [ -f "docs/ENV_REFERENCE.md" ] || [ -f "ENV_REFERENCE.md" ]; then
    echo "✅ ENV_REFERENCE.md found"
else
    echo "⚠️  WARN: ENV_REFERENCE.md not found"
    WARNINGS=$((WARNINGS + 1))
fi

# Check docker-compose.dev.yml references env_file
if grep -q "env_file:" docker-compose.dev.yml 2>/dev/null && grep -q "\.env\.dev" docker-compose.dev.yml 2>/dev/null; then
    echo "✅ docker-compose.dev.yml references .env.dev"
else
    echo "❌ FAIL: docker-compose.dev.yml does not reference env_file: .env.dev for backend/frontends"
    FAILED=1
fi

echo ""

# ============================================================================
# B) ENVIRONMENT VARIABLES
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "B) ENVIRONMENT VARIABLES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ ! -f ".env.dev" ]; then
    echo "⚠️  Skipping variable checks (no .env.dev)"
    WARNINGS=$((WARNINGS + 1))
else
    # Required variables
    REQUIRED_VARS=(
        "NEXT_PUBLIC_API_BASE_URL"
        "DATABASE_URL"
        "REDIS_URL"
        "SECRET_KEY"
    )
    
    MISSING_VARS=()
    for var in "${REQUIRED_VARS[@]}"; do
        # Check in .env.dev first, then docker-compose.dev.yml (for dev defaults)
        if grep -q "^${var}=" .env.dev 2>/dev/null; then
            # For SECRET_KEY, check length without printing value
            if [ "$var" = "SECRET_KEY" ]; then
                SECRET_KEY_VALUE=$(grep "^${var}=" .env.dev | cut -d'=' -f2- | tr -d '"' | tr -d "'")
                if [ ${#SECRET_KEY_VALUE} -ge 32 ]; then
                    echo "  ✅ $var is set in .env.dev (length OK: ${#SECRET_KEY_VALUE} chars)"
                else
                    echo "  ❌ $var is too short (${#SECRET_KEY_VALUE} chars, need >= 32)"
                    MISSING_VARS+=("$var")
                    FAILED=1
                fi
            else
                echo "  ✅ $var is set in .env.dev"
            fi
        elif grep -q "${var}:" docker-compose.dev.yml 2>/dev/null || grep -q "${var}=" docker-compose.dev.yml 2>/dev/null; then
            # Variable is in docker-compose.dev.yml (dev defaults are acceptable)
            if [ "$var" = "SECRET_KEY" ]; then
                echo "  ⚠️  $var is set in docker-compose.dev.yml (dev default - acceptable for dev)"
            else
                echo "  ⚠️  $var is set in docker-compose.dev.yml (dev default - acceptable for dev)"
            fi
            # Don't fail for dev defaults, but warn
        else
            echo "  ❌ $var is missing (not in .env.dev or docker-compose.dev.yml)"
            MISSING_VARS+=("$var")
            FAILED=1
        fi
    done
    
    # Check CORS_ALLOW_ORIGINS
    echo ""
    echo "Checking CORS configuration..."
    if grep -q "^CORS_ALLOW_ORIGINS=" .env.dev 2>/dev/null; then
        CORS_ORIGINS=$(grep "^CORS_ALLOW_ORIGINS=" .env.dev | cut -d'=' -f2- | tr -d '"' | tr -d "'")
        if echo "$CORS_ORIGINS" | grep -q "localhost:3000" && echo "$CORS_ORIGINS" | grep -q "localhost:3001"; then
            echo "  ✅ CORS_ALLOW_ORIGINS includes localhost:3000 and localhost:3001"
        else
            echo "  ❌ FAIL: CORS_ALLOW_ORIGINS must include localhost:3000 and localhost:3001"
            echo "     Found: $CORS_ORIGINS"
            FAILED=1
        fi
    else
        echo "  ⚠️  WARN: CORS_ALLOW_ORIGINS not set in .env.dev (may use docker-compose defaults)"
        WARNINGS=$((WARNINGS + 1))
    fi
    
    # Check storage configuration (if enabled)
    echo ""
    echo "Checking storage configuration..."
    STORAGE_PROVIDER=$(grep "^STORAGE_PROVIDER=" .env.dev 2>/dev/null | cut -d'=' -f2- | tr -d '"' | tr -d "'" || echo "")
    S3_BUCKET=$(grep "^S3_BUCKET=" .env.dev 2>/dev/null | cut -d'=' -f2- | tr -d '"' | tr -d "'" || echo "")
    
    if [ -n "$STORAGE_PROVIDER" ] && [ "$STORAGE_PROVIDER" != "none" ] || [ -n "$S3_BUCKET" ]; then
        echo "  ℹ️  Storage is enabled, checking required variables..."
        STORAGE_VARS=(
            "S3_BUCKET"
            "S3_ACCESS_KEY_ID"
            "S3_SECRET_ACCESS_KEY"
            "S3_ENDPOINT_URL"
            "S3_REGION"
        )
        
        STORAGE_MISSING=0
        for var in "${STORAGE_VARS[@]}"; do
            if grep -q "^${var}=" .env.dev 2>/dev/null; then
                # Mask value for security
                VALUE=$(grep "^${var}=" .env.dev | cut -d'=' -f2- | tr -d '"' | tr -d "'")
                MASKED_VALUE="${VALUE:0:4}...${VALUE: -4}"
                echo "  ✅ $var is set (${MASKED_VALUE})"
            else
                echo "  ❌ $var is missing"
                STORAGE_MISSING=$((STORAGE_MISSING + 1))
            fi
        done
        
        if [ $STORAGE_MISSING -gt 0 ]; then
            echo "  ⚠️  WARN: Storage enabled but $STORAGE_MISSING variable(s) missing"
            WARNINGS=$((WARNINGS + 1))
        fi
    else
        echo "  ℹ️  Storage is not configured (optional)"
    fi
fi

echo ""

# ============================================================================
# C) DOCKER SERVICES
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "C) DOCKER SERVICES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if ! command -v docker &> /dev/null; then
    echo "❌ FAIL: Docker not found"
    FAILED=1
elif ! docker info > /dev/null 2>&1; then
    echo "❌ FAIL: Docker is not running"
    FAILED=1
else
    echo "✅ Docker is running"
    echo ""
    
    # Check container status
    CONTAINERS=$(docker compose -f docker-compose.dev.yml ps --format json 2>/dev/null || echo "[]")
    
    if echo "$CONTAINERS" | grep -q "exited" || docker compose -f docker-compose.dev.yml ps 2>/dev/null | grep -q "Exited"; then
        echo "❌ FAIL: Some containers are exited"
        docker compose -f docker-compose.dev.yml ps
        FAILED=1
    else
        echo "✅ All containers are running"
        docker compose -f docker-compose.dev.yml ps
    fi
    
    # Check backend logs for errors
    echo ""
    echo "Checking backend logs for errors..."
    BACKEND_LOGS=$(docker compose -f docker-compose.dev.yml logs --tail=50 backend 2>/dev/null || echo "")
    
    if echo "$BACKEND_LOGS" | grep -qiE "(error|exception|traceback|AmbiguousForeignKeysError|InvalidRequestError)"; then
        echo "  ⚠️  WARN: Found errors in backend logs:"
        echo "$BACKEND_LOGS" | grep -iE "(error|exception|traceback|AmbiguousForeignKeysError|InvalidRequestError)" | tail -5
        WARNINGS=$((WARNINGS + 1))
    else
        echo "  ✅ No critical errors in backend logs"
    fi
    
    # Check for CORS/storage issues
    if echo "$BACKEND_LOGS" | grep -qiE "(cors|storage.*not.*configured|StorageNotConfiguredError)"; then
        echo "  ⚠️  WARN: CORS or storage warnings in logs"
        echo "$BACKEND_LOGS" | grep -iE "(cors|storage.*not.*configured|StorageNotConfiguredError)" | tail -3
        WARNINGS=$((WARNINGS + 1))
    fi
fi

echo ""

# ============================================================================
# D) API LIVE CHECKS
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "D) API LIVE CHECKS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check OpenAPI endpoint
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/openapi.json 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Backend OpenAPI endpoint accessible (HTTP $HTTP_CODE)"
else
    echo "❌ FAIL: Backend OpenAPI endpoint not accessible (HTTP $HTTP_CODE)"
    FAILED=1
fi

# Check CORS preflight
echo ""
echo "Checking CORS preflight..."
CORS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X OPTIONS \
    -H "Origin: http://localhost:3001" \
    -H "Access-Control-Request-Method: GET" \
    -H "Access-Control-Request-Headers: authorization,content-type" \
    http://localhost:8000/api/v1/offers 2>/dev/null || echo "000")

if [ "$CORS_RESPONSE" = "200" ] || [ "$CORS_RESPONSE" = "204" ]; then
    # Check headers
    CORS_HEADERS=$(curl -s -I -X OPTIONS \
        -H "Origin: http://localhost:3001" \
        -H "Access-Control-Request-Method: GET" \
        http://localhost:8000/api/v1/offers 2>/dev/null || echo "")
    
    if echo "$CORS_HEADERS" | grep -qi "Access-Control-Allow-Origin"; then
        if echo "$CORS_HEADERS" | grep -qi "Access-Control-Allow-Credentials"; then
            echo "✅ CORS preflight OK (includes Allow-Origin and Allow-Credentials)"
        else
            echo "⚠️  WARN: CORS preflight OK but missing Allow-Credentials header"
            WARNINGS=$((WARNINGS + 1))
        fi
    else
        echo "❌ FAIL: CORS preflight response missing Access-Control-Allow-Origin"
        FAILED=1
    fi
else
    echo "❌ FAIL: CORS preflight failed (HTTP $CORS_RESPONSE)"
    FAILED=1
fi

echo ""

# ============================================================================
# E) FRONTEND SMOKE TESTS
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "E) FRONTEND SMOKE TESTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check frontend-client
CLIENT_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "000")
if [ "$CLIENT_CODE" = "200" ] || [ "$CLIENT_CODE" = "302" ]; then
    echo "✅ Frontend-client accessible (HTTP $CLIENT_CODE)"
else
    echo "⚠️  WARN: Frontend-client not accessible (HTTP $CLIENT_CODE)"
    WARNINGS=$((WARNINGS + 1))
fi

# Check frontend-admin
ADMIN_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3001 2>/dev/null || echo "000")
if [ "$ADMIN_CODE" = "200" ] || [ "$ADMIN_CODE" = "302" ]; then
    echo "✅ Frontend-admin accessible (HTTP $ADMIN_CODE)"
else
    echo "⚠️  WARN: Frontend-admin not accessible (HTTP $ADMIN_CODE)"
    WARNINGS=$((WARNINGS + 1))
fi

echo ""

# ============================================================================
# SUMMARY
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ $FAILED -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo "✅ AUDIT PASSED: All checks passed"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
elif [ $FAILED -eq 0 ]; then
    echo "⚠️  AUDIT PASSED WITH WARNINGS: $WARNINGS warning(s)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
else
    echo "❌ AUDIT FAILED: $FAILED failure(s), $WARNINGS warning(s)"
    if [ ${#MISSING_VARS[@]} -gt 0 ]; then
        echo ""
        echo "Missing required variables: ${MISSING_VARS[*]}"
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 1
fi
