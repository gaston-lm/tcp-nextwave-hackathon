#!/usr/bin/env python3
"""Replay a transaction CSV at a fixed rate to simulate a live feed."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections.abc import Callable, Iterable
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

try:
    from .load_history import (
        IngestionError,
        Transaction,
        database_config,
        insert_transactions,
        iter_transactions,
    )
except ImportError:  # Allows `python scripts/ingestion/stream_ingest.py ...`.
    from load_history import (
        IngestionError,
        Transaction,
        database_config,
        insert_transactions,
        iter_transactions,
    )


def replay_transactions(
    transactions: Iterable[Transaction],
    rows_per_second: float,
    batch_size: int,
    insert_batch: Callable[[list[Transaction]], int],
    transaction_id_offset: int = 0,
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
        batch.append(
            replace(
                transaction,
                transaction_id=transaction.transaction_id + transaction_id_offset,
                issued_timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )

        if len(batch) == batch_size:
            inserted += insert_batch(batch)
            logging.info("Inserted %d rows so far.", inserted)
            batch = []

    if batch:
        inserted += insert_batch(batch)
        logging.info("Inserted %d rows so far.", inserted)
    return inserted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Replay a payment CSV as a paced live stream."
    )
    parser.add_argument("csv_file", type=Path, help="Path to the input CSV file")
    parser.add_argument(
        "--rows-per-second", type=float, default=10.0, help="Replay rate (default: 10)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=25,
        help="Rows per database insert (default: 25)",
    )
    parser.add_argument(
        "--transaction-id-offset",
        type=int,
        default=0,
        help="Value added to each source transaction ID to avoid conflicts (default: 0).",
    )
    args = parser.parse_args(argv)

    if args.rows_per_second <= 0:
        parser.error("--rows-per-second must be greater than zero")
    if args.batch_size <= 0:
        parser.error("--batch-size must be greater than zero")
    if args.transaction_id_offset < 0:
        parser.error("--transaction-id-offset must not be negative")

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        try:
            import psycopg2
            from dotenv import load_dotenv
        except ModuleNotFoundError as error:
            raise IngestionError(
                "Missing dependency. Install requirements with: pip install -r requirements.txt"
            ) from error

        load_dotenv(dotenv_path=Path(__file__).parents[2] / "data" / ".env")
        logging.info("Streaming and validating %s...", args.csv_file)
        transactions = iter_transactions(args.csv_file)
        logging.info(
            "Replaying at %.2f rows/second in batches of %d with transaction ID offset %d. Press Ctrl+C to stop.",
            args.rows_per_second,
            args.batch_size,
            args.transaction_id_offset,
        )
        with psycopg2.connect(**database_config()) as connection:
            inserted = replay_transactions(
                transactions,
                args.rows_per_second,
                args.batch_size,
                lambda batch: insert_transactions(connection, batch),
                transaction_id_offset=args.transaction_id_offset,
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
