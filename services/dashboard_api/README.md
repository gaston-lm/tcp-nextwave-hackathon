# Dashboard API

FastAPI backend consumed by the React dashboard. It stores operational incidents
in PostgreSQL and runs on port `8000`.

## Run locally

Configure the shared database in `data/.env`, then initialize it from the
repository root:

```bash
make db-up
make db-init HISTORY=data/local/baseline.csv
pip install -r services/dashboard_api/requirements.txt
make dashboard-api
```

Open the interactive API documentation at `http://127.0.0.1:8000/docs`.

## Endpoints

- `GET /health`
- `GET /api/incidents`
- `GET /api/incidents/{incident_id}`
- `POST /api/incidents`
- `PATCH /api/incidents/{incident_id}/read` — persist an incident's read state with `{ "is_read": true | false }`
- `GET /api/dashboard/incidents-today` — incidents created today and their severity breakdown
- `GET /api/dashboard/incidents-this-week` — week-to-date incidents grouped by database creation date
- `GET /api/dashboard/transaction-trend` — transaction and failure counts for the latest 12 hours

## Dashboard data

`make db-init` applies the incident schema and loads the deterministic sample
incidents in `data/seeds/dashboard_mock.sql`. The dashboard uses those records
to show read/unread tabs, severity slices for today's chart, and week-to-date
incident counts. The sample seed is idempotent, so it can safely be re-run
during local development.
