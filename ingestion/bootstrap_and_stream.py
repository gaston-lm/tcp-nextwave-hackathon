#!/usr/bin/env python3
"""Bulk-load the first 20% of a CSV, then replay the rest as a live stream."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

try:
    from .ingest import IngestionError, database_config, insert_transactions, iter_transactions
    from .stream_ingest import bootstrap_then_stream, count_csv_rows
except ImportError:
    from ingest import IngestionError, database_config, insert_transactions, iter_transactions
    from stream_ingest import bootstrap_then_stream, count_csv_rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap 20% of a CSV, then stream the remainder.")
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--rows-per-second", type=float, default=10.0)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--bootstrap-batch-size", type=int, default=1000)
    args = parser.parse_args(argv)
    if min(args.rows_per_second, args.batch_size, args.bootstrap_batch_size) <= 0:
        parser.error("all rates and batch sizes must be greater than zero")

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        from dotenv import load_dotenv
        import psycopg2
        load_dotenv(dotenv_path=Path(__file__).parents[1] / "data" / ".env")
        total_rows = count_csv_rows(args.csv_file)
        logging.info("Bootstrapping %d of %d rows (20%%).", total_rows // 5, total_rows)
        with psycopg2.connect(**database_config()) as connection:
            inserted = bootstrap_then_stream(
                iter_transactions(args.csv_file), total_rows,
                lambda batch: insert_transactions(connection, batch),
                args.rows_per_second, args.batch_size, bootstrap_batch_size=args.bootstrap_batch_size,
            )
        logging.info("Finished. Inserted %d new rows.", inserted)
        return 0
    except KeyboardInterrupt:
        logging.info("Stream stopped by user.")
        return 0
    except (IngestionError, OSError) as error:
        logging.error("Error: %s", error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
