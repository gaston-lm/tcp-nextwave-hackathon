#!/usr/bin/env python3
"""Apply schema, load history, and calculate diagnostic baselines."""

import argparse
import os
import sys
from datetime import timedelta
from pathlib import Path

import psycopg2
from psycopg2.errors import DuplicateTable
from dotenv import load_dotenv


ROOT = Path(__file__).parents[1]
DEFINITIONS = Path(__file__).parent / "db_table_definitions"
TEST_DASHBOARD_SEED = Path(__file__).parent / "test_mock_dashboard.sql"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingestion.load_history import insert_transactions, read_transactions


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply schema, load history, and refresh weekday baselines."
    )
    parser.add_argument(
        "--history-csv",
        type=Path,
        required=True,
        help="Historical transaction CSV used to build the baseline metrics.",
    )
    args = parser.parse_args()
    load_dotenv(Path(__file__).with_name(".env"))
    connection_config = {
        "host": os.environ["POSTGRES_HOST"],
        "port": os.environ["POSTGRES_PORT"],
        "dbname": os.environ["POSTGRES_DB"],
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
    }
    table_files = (
        "methods_by_provider.sql",
        "providers_by_merchant.sql",
        "transactions.sql",
        "incidents.sql",
        "baseline_metrics.sql",
    )
    with psycopg2.connect(**connection_config) as connection:
        with connection.cursor() as cursor:
            for filename in table_files:
                cursor.execute("SAVEPOINT apply_definition")
                try:
                    cursor.execute((DEFINITIONS / filename).read_text(encoding="utf-8"))
                except DuplicateTable:
                    cursor.execute("ROLLBACK TO SAVEPOINT apply_definition")
            history = read_transactions(args.history_csv)
            inserted = insert_transactions(connection, history)
            cursor.execute("""
                SELECT MIN(issued_timestamp), MAX(issued_timestamp)
                FROM transactions
            """)
            history_start, history_end = cursor.fetchone()
            if history_start is None:
                raise RuntimeError("No transactions were loaded; baseline metrics cannot be calculated.")
            cursor.execute(
                "SELECT refresh_baseline_metrics(%s, %s)",
                (history_start, history_end + timedelta(microseconds=1)),
            )
            cursor.execute("SELECT COUNT(*) FROM baseline_metrics")
            baseline_rows = cursor.fetchone()[0]
            cursor.execute(TEST_DASHBOARD_SEED.read_text(encoding="utf-8"))
    print(
        f"Database schema, dashboard seed, and baselines are ready. Loaded {inserted} "
        f"history rows and built {baseline_rows} baseline metric rows."
    )


if __name__ == "__main__":
    main()
