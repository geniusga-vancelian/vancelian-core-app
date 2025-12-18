#!/bin/bash
# Script to create Alembic migration
# Usage: ./create_migration.sh

cd "$(dirname "$0")"
alembic revision --autogenerate -m "Initial schema: users, accounts, operations, ledger_entries, audit_logs"
