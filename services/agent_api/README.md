# Agent API

FastAPI service implementing the Control Tower investigation orchestration. Its first specialist,
`AnomalyDetector`, compares a current five-minute window with weekday baseline metrics. The model
can call typed, read-only Postgres metric tools; it cannot issue SQL directly.

## Run locally

Configure shared PostgreSQL settings in `data/.env`, then initialize the database from the
repository root:

```sh
make db-up
make db-init HISTORY=data/local/baseline.csv
python -m venv .venv
. .venv/bin/activate
pip install -r services/agent_api/requirements.txt
cp services/agent_api/.env.example services/agent_api/.env
make agent-api
```

Set `OPENAI_API_KEY` in `services/agent_api/.env`. The agent API runs on port `8001`,
keeping port `8000` available for the dashboard API.

Run payment anomaly detection. It analyzes the latest *completed* five-minute bucket;
pass `as_of` to make a demo or test use a specific point in time.

```sh
curl -X POST http://localhost:8001/investigations \
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
