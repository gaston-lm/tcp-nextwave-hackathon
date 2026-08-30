# Control Tower database

This folder owns the shared PostgreSQL schema and local Docker database.

## Start automatically with Docker

Create a local configuration file and set a non-empty password:

```bash
cp data/.env.example data/.env
```

Start PostgreSQL in the background:

```bash
docker compose -f data/docker-compose.yml up -d
```

The service is named `control-tower-postgres`, listens on port `5432`, and uses the database name `control_tower_database`. `restart: unless-stopped` makes Docker start it again after Docker Desktop or the host restarts, unless you explicitly stop it.

## Initialize schema, history, and baselines

The Docker service loads table definitions only when it creates a new volume. Initialize
an already-running database by loading the historical transaction CSV and calculating all
weekday baseline grains:

```bash
python data/init_db.py --history-csv path/to/history.csv
```

The script applies the schema, inserts the CSV's mapping and transaction rows, then calls
`refresh_baseline_metrics`. Baselines are calculated only after history is present, so they
never include an empty database or predate the history load.

## Reset local data

This removes the local database volume and all of its contents:

```bash
docker compose -f data/docker-compose.yml down -v
docker compose -f data/docker-compose.yml up -d
python data/init_db.py --history-csv path/to/history.csv
```

## Connect with psql

```bash
docker exec -it control-tower-postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```
