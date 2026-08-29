# Control Tower API

FastAPI backend for the React dashboard. It stores operational incidents in PostgreSQL. Their SQL definitions live with the rest of the repository schema in `data/db_table_definitions/`.

## Setup

The API reuses the local PostgreSQL configuration in `ingestion/.env`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt
python data/init_db.py
uvicorn api.main:app --reload --port 8000
```

Open the interactive API documentation at `http://127.0.0.1:8000/docs`.

## Tables

- `incidents` stores operational incidents, their impact metrics, and the agent action summary shown in the dashboard.

## Endpoints

- `GET /health`
- `GET /api/incidents`
- `GET /api/incidents/{incident_key}`
- `POST /api/incidents`
