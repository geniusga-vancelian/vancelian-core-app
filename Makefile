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


