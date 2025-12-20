#!/bin/bash
# One-command dev startup script
# Starts all services and waits for backend to be healthy

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "=================================================================================="
echo "🚀 VANCELIAN DEV STARTUP"
echo "=================================================================================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker Desktop."
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Check .env.dev
if [ ! -f ".env.dev" ]; then
    echo "⚠️  .env.dev not found"
    if [ -f ".env.dev.example" ]; then
        echo "   Creating .env.dev from .env.dev.example..."
        cp .env.dev.example .env.dev
        echo "   ✅ Created .env.dev (please review and update if needed)"
    else
        echo "   ❌ .env.dev.example not found. Please create .env.dev manually."
        echo "   Required variables:"
        echo "     - DATABASE_URL"
        echo "     - REDIS_URL"
        echo "     - SECRET_KEY (min 32 chars)"
        echo "     - NEXT_PUBLIC_API_BASE_URL (for frontends)"
        echo "     - CORS_ALLOW_ORIGINS (comma-separated)"
        exit 1
    fi
    echo ""
else
    echo "✅ .env.dev found"
    echo ""
fi

# Start services
echo "Starting Docker services..."
docker compose -f docker-compose.dev.yml up -d --build

echo ""
echo "Waiting for backend to be healthy (max 30s)..."

# Wait for backend health (max 30 seconds)
MAX_WAIT=30
WAIT_INTERVAL=2
ELAPSED=0
BACKEND_HEALTHY=false

while [ $ELAPSED -lt $MAX_WAIT ]; do
    if curl -s -f -m 2 http://localhost:8000/health > /dev/null 2>&1; then
        BACKEND_HEALTHY=true
        break
    fi
    
    # Try /docs as fallback
    if curl -s -f -m 2 http://localhost:8000/docs > /dev/null 2>&1; then
        BACKEND_HEALTHY=true
        break
    fi
    
    echo -n "."
    sleep $WAIT_INTERVAL
    ELAPSED=$((ELAPSED + WAIT_INTERVAL))
done

echo ""

if [ "$BACKEND_HEALTHY" = true ]; then
    echo "✅ Backend is healthy"
else
    echo "❌ Backend health check failed after ${MAX_WAIT}s"
    echo ""
    echo "Checking backend logs..."
    docker compose -f docker-compose.dev.yml logs --tail=20 backend
    echo ""
    echo "Please check the logs above for errors."
    exit 1
fi

# Display service status
echo ""
echo "=================================================================================="
echo "✅ SERVICES RUNNING"
echo "=================================================================================="
echo ""
echo "📱 Frontend Client:  http://localhost:3000"
echo "🔧 Frontend Admin:   http://localhost:3001"
echo "🌐 Backend API:      http://localhost:8000"
echo "📚 API Docs:         http://localhost:8000/docs"
echo ""
echo "To view logs:"
echo "  docker compose -f docker-compose.dev.yml logs -f"
echo ""
echo "To stop services:"
echo "  docker compose -f docker-compose.dev.yml down"
echo ""
echo "=================================================================================="

