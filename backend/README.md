# Control Tower backend

FastAPI service implementing a bounded ReAct payment anomaly detection agent. The model can call
typed, read-only Postgres metric tools; it cannot issue SQL directly.

## Run locally

From the repository root, start Postgres first:

```sh
docker compose up -d
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
set -a; source backend/.env; set +a
uvicorn backend.app.main:app --reload
```

After loading historic transaction data, build the stored weekday baseline:

```sql
SELECT refresh_baseline_metrics('2026-07-01 00:00:00', '2026-08-29 00:00:00');
```

For a reproducible local scenario, run `data/demo/seed_agent_demo.sql`. It creates
a Monday 14:00 baseline near 95% approval and a current window with an Adyen/Brazil
card decline spike. Investigate it with `as_of` set to `2026-08-31T14:05:00`.

Run payment anomaly detection. It analyzes the latest *completed* five-minute bucket;
pass `as_of` to make a demo or test use a specific point in time.

```sh
curl -X POST http://localhost:8000/investigations \
  -H 'content-type: application/json' \
  -d '{
    "as_of":"2026-08-29T14:05:00"
  }'
```

## Arize AX tracing

The agent, its database tools, and OpenAI calls are traced when all Arize AX
settings are present. Configure your own Arize region endpoint—this project does
use the US collector by default:

```env
ARIZE_SPACE_ID=...
ARIZE_API_KEY=...
ARIZE_PROJECT_NAME=control-tower
ARIZE_COLLECTOR_ENDPOINT=https://otlp.arize.com/v1
```

Restart Uvicorn after setting these values, then run an investigation to export
the trace. The agent creates an AGENT span, each metric tool creates a TOOL span,
and OpenAI calls are automatically instrumented.
