![crew_card](docs/img/crew-card.png)

### TCP Group - Nextwave Hackathon 2026 by Yuno x Nauta

TCP's repository for Nextwave Hackathon 2026 by Yuno x Nauta 

Challange 2: The Control Tower

See [ARCHITECTURE.md](ARCHITECTURE.md) for the high-level product architecture.

## Local development

Database credentials live in `data/.env`; start from `data/.env.example`.
Place large, local-only CSV files in `data/local/`, for example
`data/local/baseline.csv`.

For local development, `data/.env` is the source of truth for database
credentials. The `make db-init` and `make agent-api` commands deliberately
discard inherited `DATABASE_URL` and `POSTGRES_*` shell variables, preventing
stale terminal or direnv credentials from overriding that file.

```bash
make db-up
make db-init HISTORY=data/local/baseline.csv
```

Run each application in a separate terminal:

```bash
make dashboard-api  # http://127.0.0.1:8000
make agent-api      # http://127.0.0.1:8001
make dashboard      # Vite development server
```

## Recreate the local demo environment

The full historical baseline is local-only and intentionally ignored by Git.
Place it at `data/local/baseline.csv` before initialization. The current demo
baseline contains one million historical transactions.

To recreate the database from scratch, including the schema, seeded dashboard
incidents, and weekday baseline metrics:

```bash
docker compose -f data/docker-compose.yml down -v
make db-up
make db-init HISTORY=data/local/baseline.csv
```

Start each local service in its own terminal:

```bash
make dashboard-api          # http://127.0.0.1:8000
make agent-api              # http://127.0.0.1:8001
make dashboard              # http://127.0.0.1:5173
make ingestion-generator    # http://127.0.0.1:8002
```

The Generator continues from one second after the newest stored transaction
timestamp. It produces one second of timestamps per real second while keeping
the configured transaction average per minute. The agent analyzes the latest
completed one-minute window. To run it once per minute during the demo, add the
following entry with `crontab -e`, replacing the repository path:

```cron
* * * * * cd /absolute/path/to/repo && .venv/bin/python scripts/agent/run_scheduled_investigation.py >> /tmp/control-tower-agent-scheduler.log 2>&1
```

The job safely skips when the Generator is stopped. Follow its output with:

```bash
tail -f /tmp/control-tower-agent-scheduler.log
```

## Repository layout

```text
.
├── apps/
│   └── dashboard/              # React/Vite dashboard
├── services/
│   ├── dashboard_api/          # Dashboard FastAPI API (port 8000)
│   └── agent_api/              # Agent orchestration FastAPI API (port 8001)
├── data/
│   ├── db_migrations/          # Ordered, versioned database changes
│   ├── schemas/                # Transaction and baseline schema definitions
│   ├── seeds/                  # Deterministic SQL seed data
│   ├── fixtures/               # Small committed example datasets
│   ├── local/                  # Ignored local CSV datasets
│   └── docker-compose.yml
├── scripts/
│   ├── db/init_db.py           # Schema, history, and baseline initialization
│   └── ingestion/              # History load, live replay, and status scripts
├── docs/                       # Challenge documentation and decision log
├── Makefile                    # Local development commands
└── requirements-dev.txt        # Shared development tooling
```

## Incident workflow

The agent API runs a three-stage incident workflow:

1. `AnomalyDetector` analyzes the latest completed one-minute payment window and returns a
   strict JSON Schema result.
2. `IncidentReviewer` compares that result with all open incidents and
   uses semantic searches over closed-incident memory and payment deployment logs.
3. A deterministic SQLAlchemy persistence stage—not an agent—creates new incidents and applies
   complete updates to existing ones in a transaction.
4. `ActionTaker` runs only for newly created incidents. It records one draft-only operational
   action per incident: deployment rollback guidance takes priority, then a merchant-approved
   provider-switch recommendation with provider-escalation draft, then a shared Slack alert draft.

Incident, incident-memory, deployment-log, and incident-action persistence use SQLAlchemy models. Analytical
transaction/baseline queries remain parameterized read-only metric queries. The investigation API
response includes the detector result, reviewer proposals, and the IDs committed by persistence.

All incident schema changes belong in `data/db_migrations/`; `scripts/db/init_db.py` records
applied migration filenames in `schema_migrations`.

## Developer checks

Install the API and shared development dependencies, then activate the hooks once per clone:

```bash
pip install -r requirements-dev.txt
pre-commit install --hook-type pre-commit --hook-type commit-msg
```

Commits must follow Conventional Commits, for example `feat: add incident memory`
or `fix(agent): handle an empty baseline`. Run all Python lint and format checks
at any time with:

```bash
make lint
```
