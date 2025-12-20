.PHONY: up down logs migrate test shell

up:
	cd infra && docker compose up -d

down:
	cd infra && docker compose down

logs:
	cd infra && docker compose logs -f

logs-backend:
	cd infra && docker compose logs -f backend

logs-worker:
	cd infra && docker compose logs -f worker

migrate:
	cd infra && docker compose exec backend alembic upgrade head

migrate-create:
	cd infra && docker compose exec backend alembic revision --autogenerate -m "$(msg)"

test:
	cd infra && docker compose exec backend pytest

shell:
	cd infra && docker compose exec backend /bin/bash

shell-db:
	cd infra && docker compose exec postgres psql -U vancelian -d vancelian_core

audit-db:
	@echo "Running database schema audit..."
	@docker compose -f docker-compose.dev.yml cp scripts/audit_db_schema.py backend:/tmp/audit_db_schema.py
	@docker compose -f docker-compose.dev.yml exec backend python3 /tmp/audit_db_schema.py


dev-up:
	@sh scripts/dev_up.sh

audit-runtime:
	@sh scripts/audit_runtime_env.sh

audit-hardcode:
	@sh scripts/check_env_hardcode.sh


