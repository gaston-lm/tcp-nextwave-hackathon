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

## Apply schema and local seed data

The Docker service loads table definitions only when it creates a new volume. Apply all schema files and local dashboard seed data to an already-running database with:

```bash
python data/init_db.py
```

## Reset local data

This removes the local database volume and all of its contents:

```bash
docker compose -f data/docker-compose.yml down -v
docker compose -f data/docker-compose.yml up -d
python data/init_db.py
```

## Connect with psql

```bash
docker exec -it control-tower-postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```
