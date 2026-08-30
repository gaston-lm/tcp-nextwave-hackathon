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

## Browser access

The API permits the local Vite dashboard and Control Tower's Vercel production
domain, including Vercel's unique production deployment URLs. This lets the
deployed dashboard call a temporary public API tunnel during the demo.

## Endpoints

- `GET /health`
- `GET /api/incidents` — open incidents for the dashboard list
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

When ActionTaker has recorded actions in `incidents_actions`, incident list and detail
responses include them in `actions`. Each item contains `actionType`, `actionDetails`, and
`createdAt`. The legacy latest-action fields (`agentAction`, `agentActionType`, and
`agentActionAt`) remain available. These are operator-facing drafts; the dashboard API does
not send Slack messages or contact payment providers.
