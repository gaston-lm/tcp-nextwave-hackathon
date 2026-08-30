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
- `GET /api/incidents/{incident_key}`
- `POST /api/incidents`
