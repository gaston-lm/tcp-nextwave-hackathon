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

- `apps/dashboard/` — React dashboard.
- `services/dashboard_api/` — FastAPI API consumed by the dashboard.
- `services/agent_api/` — FastAPI API and multi-agent investigation workflow.
- `data/` — PostgreSQL Compose configuration, schema, seeds, fixtures, and database initialization.
- `scripts/` — database initialization, historical loading, and live transaction replay utilities.
- `docs/` — challenge and product documentation.

Each component has its own README with setup and usage details.
