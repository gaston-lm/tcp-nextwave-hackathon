![crew_card](docs/img/crew-card.png)

### TCP Group - Nextwave Hackathon 2026 by Yuno x Nauta

TCP's repository for Nextwave Hackathon 2026 by Yuno x Nauta 

Challange 2: The Control Tower

## Local development

Database credentials live in `data/.env`; start from `data/.env.example`.
Place large, local-only CSV files in `data/local/`, for example
`data/local/baseline.csv`.

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

## Repository layout

```text
.
├── apps/
│   └── dashboard/              # React/Vite dashboard
├── services/
│   ├── dashboard_api/          # Dashboard FastAPI API (port 8000)
│   └── agent_api/              # Agent orchestration FastAPI API (port 8001)
├── data/
│   ├── schemas/                # PostgreSQL schema definitions
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

## Developer checks

Install the shared development tools and activate the hooks once per clone:

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
