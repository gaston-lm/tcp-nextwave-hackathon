# Payment transaction ingestion

This folder contains historical CSV loading, legacy CSV replay, and PostgreSQL status tools.

## Setup

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r scripts/ingestion/requirements.txt
```

See [the shared database README](../data/README.md) to configure and start PostgreSQL.

## CSV format

The CSV header must be:

```text
country,provider_name,provider_id,method_name,method_id,merchant_name,merchant_id,issuing_bank,receiving_bank,transaction_id,issued_timestamp,is_declined,decline_code,currency,value_transaction_currency,value
```

The importer upserts provider/method mappings before inserting transactions. Boolean values may be `true`, `false`, `1`, or `0`; timestamps use ISO-8601.

## Load history

Load a finite historical CSV while preserving each source `issued_timestamp`. By default, the
loader reads the table's current maximum `transaction_id`, sorts CSV rows by `issued_timestamp`
(retaining CSV order for equal timestamps), and assigns consecutive IDs. This makes scenario
files with reused source IDs safe to load one after another.

```bash
python scripts/ingestion/load_history.py data/fixtures/transactions.example.csv
```

Use `--preserve-transaction-ids` only when source IDs are already globally unique:

```bash
python scripts/ingestion/load_history.py data/fixtures/transactions.example.csv \
  --preserve-transaction-ids
```

## Generator-controlled live stream

The current live feed is generated directly by the Generator UI; it does not require a
CSV. Start the database, run `make ingestion-generator`, and use **Start live ingestion** at
`http://127.0.0.1:8002`. Each real second inserts one second of transaction timestamps,
while preserving the configured average transaction rate over time. Minute-level volume varies so
the live dashboard reflects natural activity changes.

## Legacy CSV replay

Replay a CSV at a controlled rate. Before each row is inserted, the loader overwrites its source `issued_timestamp` with the current UTC time. Use this only for legacy/manual replay; it is not the Generator-controlled live feed.

```bash
python scripts/ingestion/stream_ingest.py data/local/transactions.csv --rows-per-second 10 --batch-size 25
```

When replaying a file whose transaction IDs already exist in the historical load, pass an
offset above the current maximum ID so the simulated live rows can be inserted:

```bash
python scripts/ingestion/stream_ingest.py data/local/transactions.csv --transaction-id-offset 1000000
```

Stop it with `Ctrl+C` (or `kill <PID>`). Completed batches remain committed.

## Check database status

```bash
python scripts/ingestion/check_db.py
```

This reports the total transaction count and oldest/newest transaction timestamps.

## Tests

```bash
pip install pytest
pytest scripts/ingestion/tests
```
