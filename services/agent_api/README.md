# Agent API

FastAPI service implementing the Control Tower investigation orchestration. Its first specialist,
`AnomalyDetector`, compares a current one-minute window with weekday baseline metrics. Its
validated output is passed to `IncidentReviewer`, which returns proposals for new or updated
incidents. Both stages use strict JSON Schema Structured Outputs and can only call typed tools;
they cannot issue SQL directly.

## Orchestration

```mermaid
flowchart LR
    subgraph Detection[" "]
        direction TB
        Detector([AnomalyDetector])
        Baseline[baseline_metrics]
        LatestTransactions[latest_transactions]
        BaselineMetrics[(baseline_metrics)]
        Transactions[(transactions)]
        Detector --> Baseline --> BaselineMetrics
        Detector --> LatestTransactions --> Transactions
    end

    subgraph Review[" "]
        direction TB
        Reviewer([IncidentReviewer])
        ClosedMemory[closed incident memory\nsemantic-search]
        DeployLogs[latest deployment logs]
        IncidentWriter[incident writer\ndeterministic process]
        IncidentMemory[(incident_memory)]
        DeploymentLogs[(deployment_logs)]
        Incidents[(incidents)]
        Reviewer --> ClosedMemory --> IncidentMemory
        Reviewer --> DeployLogs --> DeploymentLogs
        Reviewer --> IncidentWriter --> Incidents
    end

    subgraph Actions[" "]
        direction TB
        ActionTaker([ActionTaker])
        DeployRollback[deploy_rollback]
        ProviderAlternatives[get_merchant_provider_alternatives]
        SwitchProvider[recommend_switch_provider_to_merchant]
        SlackAlert[post_slack_alert_to_channel]
        ProviderMappings[(providers_by_merchant)]
        IncidentActions[(incidents_actions)]
        ActionTaker --> DeployRollback --> IncidentActions
        ActionTaker --> ProviderAlternatives --> ProviderMappings
        ActionTaker --> SwitchProvider --> IncidentActions
        ActionTaker --> SlackAlert --> IncidentActions
    end

    Detector --> Reviewer --> ActionTaker
    Incidents -. persisted incident .-> ActionTaker

    classDef agent fill:#e8f4ff,stroke:#2563eb,stroke-width:2px,color:#172554,font-weight:bold;
    classDef tool fill:#ffffff,stroke:#94a3b8,stroke-width:1px,color:#334155,font-size:10px;
    classDef database fill:#f8fafc,stroke:#64748b,stroke-width:1px,color:#334155,font-size:9px;
    class Detector,Reviewer,ActionTaker agent;
    class Baseline,LatestTransactions,ClosedMemory,DeployLogs,IncidentWriter,DeployRollback,ProviderAlternatives,SwitchProvider,SlackAlert tool;
    class BaselineMetrics,Transactions,IncidentMemory,DeploymentLogs,Incidents,ProviderMappings,IncidentActions database;
    style Detection fill:none,stroke:none
    style Review fill:none,stroke:none
    style Actions fill:none,stroke:none
```

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

The SQLAlchemy incident repository validates pooled database connections before checkout, so
connections made stale by a local PostgreSQL restart are transparently recreated.

Run payment anomaly detection. It analyzes the latest *completed* one-minute bucket;
pass `as_of` to make a demo or test use a specific point in time. The API resolves this to a
canonical `[started_at, last_seen_at)` window and supplies it to both agents. New incidents use
the window start as `started_at`; all proposals use its end as `last_seen_at`; updates preserve
the existing incident's `started_at`. Naive `as_of` values are interpreted as UTC.

The response contains the structured detector result, a `reviewer` result with
`new_incidents` and `updated_incidents`, the per-new-incident `action_taker` results, and both
persistence records. A deterministic SQLAlchemy writer applies reviewer and action proposals;
agents never write to the database directly. ActionTaker selects exactly one draft-only action
per new incident: linked deployment rollback guidance, otherwise an approved provider-switch
recommendation with provider escalation draft, otherwise a merchant shared-Slack alert draft.

```sh
curl -X POST http://localhost:8001/investigations \
  -H 'content-type: application/json' \
  -d '{
    "as_of":"2026-08-29T14:05:00"
  }'
```

## Demo scheduler

`scripts/agent/run_scheduled_investigation.py` runs one investigation using the
Generator UI's current simulated timestamp as `as_of`. It skips safely while
live ingestion is stopped and uses a local lock file to prevent overlapping
investigations.

Run it once from the repository root with:

```sh
make agent-scheduled-investigation
```

For the demo, a local cron entry runs it once per real minute. It requires the
agent API and Generator UI to be running first. Replace `/absolute/path/to/repo`
with the clone path:

```cron
* * * * * cd /absolute/path/to/repo && .venv/bin/python scripts/agent/run_scheduled_investigation.py >> /tmp/control-tower-agent-scheduler.log 2>&1
```

The scheduler uses the Generator's current timestamp, so each run analyzes the
latest completed one-minute window. Inspect its output with
`tail -f /tmp/control-tower-agent-scheduler.log`. It skips a tick when the stream
is stopped or an earlier investigation still holds the lock.

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
the trace. `tower_control_agent` creates a CHAIN span that contains AGENT spans for each
specialist, each metric tool creates a TOOL span, and OpenAI calls are automatically
instrumented. IncidentReviewer semantic searches for closed incidents and payment deploys are
also emitted as TOOL spans.
