# Payment transaction ingestion

This folder contains the CSV ingestion, simulated streaming, PostgreSQL status, and local Docker database tools.

## Setup

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r ingestion/requirements.txt
```

See [the shared database README](../data/README.md) to configure and start PostgreSQL.

## CSV format

The CSV header must be:

```text
country,provider_name,provider_id,method_name,method_id,merchant_name,merchant_id,issuing_bank,receiving_bank,transaction_id,issued_timestamp,is_declined,decline_code,currency,value_transaction_currency,value
```

The importer upserts provider/method mappings before inserting transactions. Boolean values may be `true`, `false`, `1`, or `0`; timestamps use ISO-8601.

## Bulk ingestion

```bash
python ingestion/ingest.py ingestion/data/example.csv
```

## Simulated live stream

Replay a CSV at a controlled rate:

```bash
python ingestion/stream_ingest.py ingestion/data/transactions.csv --rows-per-second 10 --batch-size 25
```

Stop it with `Ctrl+C` (or `kill <PID>`). Completed batches remain committed.

## Bootstrap then stream

Bulk-load the first 20% of the file in batches of 1,000, then stream the remaining rows:

```bash
python ingestion/bootstrap_and_stream.py ingestion/data/transactions.csv --rows-per-second 10 --batch-size 25
```

Transaction inserts are idempotent by `transaction_id`, so this can safely resume after a partial run.

## Check database status

```bash
python ingestion/check_db.py
```

This reports the total transaction count and oldest/newest transaction timestamps.

## Tests

```bash
pip install pytest
pytest ingestion/tests
```
