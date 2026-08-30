PYTHON ?= .venv/bin/python
HISTORY ?= data/local/baseline.csv
LIVE_FILE ?= data/local/transactions.csv
LIVE_RATE ?= 10

.PHONY: db-up db-down db-init dashboard-api agent-api dashboard ingest-live lint

db-up:
	docker compose -f data/docker-compose.yml up -d

db-down:
	docker compose -f data/docker-compose.yml down

db-init:
	$(PYTHON) scripts/db/init_db.py --history-csv $(HISTORY)

dashboard-api:
	$(PYTHON) -m uvicorn services.dashboard_api.main:app --reload --port 8000

agent-api:
	$(PYTHON) -m uvicorn services.agent_api.app.main:app --reload --port 8001

dashboard:
	npm --prefix apps/dashboard run dev

ingest-live:
	$(PYTHON) scripts/ingestion/stream_ingest.py $(LIVE_FILE) --rows-per-second $(LIVE_RATE)

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
