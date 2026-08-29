#!/usr/bin/env python3
"""Replay a transaction CSV at a fixed rate to simulate a live feed."""

from __future__ import annotations

import argparse
import csv
import logging
import sys
import time
from collections.abc import Callable, Iterable
from itertools import islice
from pathlib import Path

try:
    from .ingest import IngestionError, Transaction, database_config, insert_transactions, iter_transactions
except ImportError:  # Allows `python ingestion/stream_ingest.py ...`.
    from ingest import IngestionError, Transaction, database_config, insert_transactions, iter_transactions


def replay_transactions(
    transactions: Iterable[Transaction],
    rows_per_second: float,
    batch_size: int,
    insert_batch: Callable[[list[Transaction]], int],
) -> int:
    """Emit rows at a steady pace and insert each completed batch."""
    interval = 1 / rows_per_second
    next_row_at = time.monotonic()
    batch: list[Transaction] = []
    inserted = 0

    for transaction in transactions:
        delay = next_row_at - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        next_row_at += interval
        batch.append(transaction)

        if len(batch) == batch_size:
            inserted += insert_batch(batch)
            logging.info("Inserted %d rows so far.", inserted)
            batch = []

    if batch:
        inserted += insert_batch(batch)
        logging.info("Inserted %d rows so far.", inserted)
    return inserted


def count_csv_rows(path: Path) -> int:
    """Count data rows without loading the CSV into memory."""
    with path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.reader(csv_file)
        next(reader, None)
        return sum(1 for _ in reader)


def _batches(transactions: Iterable[Transaction], batch_size: int) -> Iterable[list[Transaction]]:
    iterator = iter(transactions)
    while batch := list(islice(iterator, batch_size)):
        yield batch


def bootstrap_then_stream(
    transactions: Iterable[Transaction],
    total_rows: int,
    insert_batch: Callable[[list[Transaction]], int],
    rows_per_second: float,
    stream_batch_size: int,
    bootstrap_percent: int = 20,
    bootstrap_batch_size: int = 1000,
) -> int:
    """Bulk-load an initial portion, then replay the remaining rows at a fixed rate."""
    bootstrap_rows = total_rows * bootstrap_percent // 100
    iterator = iter(transactions)
    inserted = 0
    for batch in _batches(islice(iterator, bootstrap_rows), bootstrap_batch_size):
        inserted += insert_batch(batch)
        logging.info("Bootstrap inserted %d of %d rows.", inserted, bootstrap_rows)
    logging.info("Bootstrap complete. Streaming the remaining %d rows.", total_rows - bootstrap_rows)
    return inserted + replay_transactions(iterator, rows_per_second, stream_batch_size, insert_batch)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay a payment CSV as a paced live stream.")
    parser.add_argument("csv_file", type=Path, help="Path to the input CSV file")
    parser.add_argument("--rows-per-second", type=float, default=10.0, help="Replay rate (default: 10)")
    parser.add_argument("--batch-size", type=int, default=25, help="Rows per database insert (default: 25)")
    args = parser.parse_args(argv)

    if args.rows_per_second <= 0:
        parser.error("--rows-per-second must be greater than zero")
    if args.batch_size <= 0:
        parser.error("--batch-size must be greater than zero")

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        try:
            from dotenv import load_dotenv
            import psycopg2
        except ModuleNotFoundError as error:
            raise IngestionError(
                "Missing dependency. Install requirements with: pip install -r requirements.txt"
            ) from error

        load_dotenv(dotenv_path=Path(__file__).parents[1] / "data" / ".env")
        logging.info("Streaming and validating %s...", args.csv_file)
        transactions = iter_transactions(args.csv_file)
        logging.info(
            "Replaying at %.2f rows/second in batches of %d. Press Ctrl+C to stop.",
            args.rows_per_second, args.batch_size,
        )
        with psycopg2.connect(**database_config()) as connection:
            inserted = replay_transactions(
                transactions,
                args.rows_per_second,
                args.batch_size,
                lambda batch: insert_transactions(connection, batch),
            )
        logging.info("Replay complete. Inserted %d rows.", inserted)
        return 0
    except KeyboardInterrupt:
        logging.info("Replay stopped by user.")
        return 0
    except (IngestionError, OSError) as error:
        logging.error("Error: %s", error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
