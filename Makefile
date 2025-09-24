.PHONY: api
api:
	cd backend && PYTHONPATH=. uv run dotenv -f ../.env run -- uv run python protocol/api/api_server.py


.PHONY: migrate.clickhouse
migrate.clickhouse:
	PYTHONPATH=backend:scripts uv run scripts/clickhouse_migrate.py --env $${ENV:-local}

.PHONY: migrate.psql
migrate.psql:
	PYTHONPATH=backend:scripts uv run scripts/psql_migrate.py --env $${ENV:-local}

.PHONY: migrate
migrate: migrate.clickhouse migrate.psql

.PHONY: local_reset
local_reset:
	PYTHONPATH=backend:scripts uv run scripts/local_reset.py

.PHONY: local_setup
local_setup: local_reset migrate

.PHONY: web
web:
	cd web && PYTHONPATH=. uv run dotenv -f ../.env run -- npm run dev


# make check_models PROVIDER=mistral
.PHONY: check_models
check_models:
	PYTHONPATH=backend:scripts uv run scripts/check_${PROVIDER}_models.py
