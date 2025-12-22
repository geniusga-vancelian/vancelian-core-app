#!/bin/bash
# Database Schema Audit Script (Bash wrapper)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check if running in Docker or locally
if [ -f /.dockerenv ] || [ -n "$DOCKER_CONTAINER" ]; then
    # Running inside Docker container
    python3 "$SCRIPT_DIR/audit_db_schema.py"
else
    # Running locally - use docker compose
    cd "$PROJECT_ROOT"
    docker compose -f docker-compose.dev.yml exec -T backend python3 scripts/audit_db_schema.py
fi

